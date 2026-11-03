import streamlit as st
import math

st.set_page_config(page_title="Aussie Solar Quote Engine", page_icon="☀️", layout="wide")

st.title("☀️ Aussie Solar & Battery Quote Engine")
st.markdown("Auto-generate system configurations and client pricing based on roof dimensions.")

# ================= 1. 销售员输入区（只有长宽、相数和利润率） =================
st.sidebar.header("🏠 Project Dimensions")
roof_l = st.sidebar.number_input("Roof Length (m)", min_value=1.0, value=9.0, step=0.5)
roof_w = st.sidebar.number_input("Roof Width (m)", min_value=1.0, value=6.0, step=0.5)
is_three_phase = st.sidebar.checkbox("Three-Phase Power?", value=False)

st.sidebar.header("💰 Sales Settings")
margin_percent = st.sidebar.slider("Target Profit Margin (%)", min_value=15, max_value=60, value=40, step=5)

# ================= 2. 彻底锁定的硬件参数（页面上完全看不到！） =================
# 如果你想改底价，只能在这里改代码
PANEL_L, PANEL_W = 1.905, 1.134
PANEL_WATT = 475
PANEL_PRICE_PER_WATT = 0.24  
INSTALL_BOS_PER_WATT = 0.30  

INVERTERS_LIST = [
    (5.0, 10.0, 1025.0, "Solinteg 5kW Single-Phase", False),
    (8.0, 16.0, 1550.0, "Solinteg 8kW Single-Phase", False),
    (10.0, 20.0, 1950.0, "Solis 10kW Three-Phase", True),
    (15.0, 30.0, 2550.0, "Solis 15kW Three-Phase", True)
]

BATTERY_KWH_PER_UNIT = 5.12
BATTERY_UNIT_COST = 800.0
SBDU_UNIT_COST = 150.0 
BATTERY_PER_SBDU = 11  

STC_PRICE, STC_YEARS = 38.0, 5.0
ELEC_PRICE, FIT_PRICE, ANNUAL_HOURS = 0.35, 0.06, 1400

# ================= 3. 核心计算逻辑 =================
@st.cache_data
def calculate_quote(roof_l, roof_w, is_three_phase, margin_percent):
    # (这里的逻辑完全不变，直接复制之前的逻辑即可)
    count_a = int(roof_l // PANEL_L) * int(roof_w // PANEL_W)
    count_b = int(roof_l // PANEL_W) * int(roof_w // PANEL_L)
    max_panels = max(count_a, count_b)
    if max_panels == 0: return None

    total_dc_kw = (max_panels * PANEL_WATT) / 1000.0
    
    selected_inv = None
    num_inverters = 1
    for inv in INVERTERS_LIST:
        cap, max_pv, cost, desc, is_3p = inv
        if is_three_phase != is_3p: continue
        if total_dc_kw > max_pv: continue
        if total_dc_kw / cap > 1.33 and cap != 5.0: continue
        selected_inv = inv
        break
        
    if not selected_inv:
        max_available_inv = max([inv for inv in INVERTERS_LIST if inv[4] == is_three_phase], key=lambda x: x[0])
        cap, max_pv, cost, desc, is_3p = max_available_inv
        num_inverters = math.ceil(total_dc_kw / max_pv)
        if (total_dc_kw / (cap * num_inverters)) > 1.33: num_inverters += 1
        selected_inv = max_available_inv
        desc = f"{num_inverters} x {desc} (Parallel)"

    battery_qty = max(3, round(total_dc_kw / BATTERY_KWH_PER_UNIT))
    sbdu_qty = math.ceil(battery_qty / BATTERY_PER_SBDU)
    total_battery_kwh = battery_qty * BATTERY_KWH_PER_UNIT

    total_raw_cost = (total_dc_kw * 1000 * PANEL_PRICE_PER_WATT) + \
                     (total_dc_kw * 1000 * INSTALL_BOS_PER_WATT) + \
                     (selected_inv[2] * num_inverters) + \
                     (battery_qty * BATTERY_UNIT_COST) + \
                     (sbdu_qty * SBDU_UNIT_COST)
                     
    selling_price = total_raw_cost / (1 - margin_percent / 100)

    stc_rebate = total_dc_kw * 1.5 * STC_PRICE * STC_YEARS
    base_rate = STC_PRICE * 14 * 0.52
    b_rebate = 0; rem = total_battery_kwh
    t1 = min(rem, 14.0); b_rebate += t1 * base_rate; rem -= t1
    if rem > 0: t2 = min(rem, 14.0); b_rebate += t2 * base_rate * 0.60; rem -= t2
    if rem > 0: t3 = min(rem, 22.0); b_rebate += t3 * base_rate * 0.15
    total_rebate = stc_rebate + b_rebate
    
    client_out_of_pocket = selling_price - total_rebate
    year1_savings = (total_dc_kw * ANNUAL_HOURS * 0.85 * ELEC_PRICE) + (total_dc_kw * ANNUAL_HOURS * 0.15 * FIT_PRICE)
    payback = client_out_of_pocket / year1_savings if year1_savings > 0 else 0

    return {
        "max_panels": max_panels, "total_dc_kw": total_dc_kw, "selected_inv": desc,
        "battery_qty": battery_qty, "total_battery_kwh": total_battery_kwh,
        "selling_price": selling_price, "stc_rebate": stc_rebate, "battery_rebate": b_rebate,
        "client_out_of_pocket": client_out_of_pocket, "year1_savings": year1_savings, "payback": payback
    }

result = calculate_quote(roof_l, roof_w, is_three_phase, margin_percent)

# ================= 4. 页面展示 =================
if result is None:
    st.error("❌ Roof area is too small for this layout!")
else:
    st.subheader("📋 System Configuration")
    col1, col2, col3 = st.columns(3)
    col1.metric("Solar Capacity", f"{result['total_dc_kw']:.2f} kW", f"{result['max_panels']} x 475W Panels")
    col2.metric("Battery Storage", f"{result['total_battery_kwh']:.2f} kWh", f"{result['battery_qty']} x Dyness Modules")
    col3.metric("Inverter", result['selected_inv'])

    st.divider()

    st.subheader("💰 Financial Breakdown & Rebates")
    st.success(f"### **Client Out-of-Pocket: ${result['client_out_of_pocket']:,.2f} AUD**")
    
    with st.expander("View Detailed Pricing & Rebates"):
        st.write(f"**Gross Selling Price:** ${result['selling_price']:,.2f}")
        st.write(f"*Includes {margin_percent}% sales margin*")
        st.write("---")
        st.write(f"**Federal STC Rebate:** -${result['stc_rebate']:,.2f}")
        st.write(f"**Federal Battery Rebate:** -${result['battery_rebate']:,.2f}")

    st.divider()

    st.subheader("📈 Estimated ROI")
    r1, r2 = st.columns(2)
    r1.metric("Year 1 Estimated Savings", f"${result['year1_savings']:,.2f} AUD")
    r2.metric("Estimated Payback Period", f"{result['payback']:.2f} Years")

    st.caption("*Disclaimer: Figures are estimates based on current market conditions. Final pricing depends on site inspection and current STC market rates.*")
