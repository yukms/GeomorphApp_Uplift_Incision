import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from geology_model import SimulationEngine

# Page configuration
st.set_page_config(layout="wide", page_title="Geomorphology Simulator")

# Inject minimal custom CSS
st.markdown("""
<style>
    .reportview-container { background: #f0f2f6; }
    .main .block-container{ padding-top: 2rem; padding-bottom: 2rem; }
    h1 { color: #2c3e50; font-family: 'Helvetica Neue', Arial, sans-serif; }
</style>
""", unsafe_allow_html=True)

if "is_running" not in st.session_state:
    st.session_state.is_running = False

def start_sim(): st.session_state.is_running = True
def stop_sim(): st.session_state.is_running = False

st.title("Grand Canyon: Variable Erosion & Uplift Simulation")

# 4. Wide panel: changed [3, 1] to [3, 2] giving the right side much more width
col1, col2 = st.columns([3, 2])

with col2:
    st.markdown("### Controls")
    
    st.markdown("#### Geological Setup")
    # 1. & 2. Default layer 30, up to 50
    num_layers = st.slider("Total Number of Rock Layers", min_value=1, max_value=50, value=30, step=1)
    
    # 3. Checkbox to turn on thickness column
    enable_thickness = st.checkbox("Enable Customizable Layer Thickness", value=False)
    
    st.markdown("**Topography Profile Customization:**")
    st.caption("Recommended Resistance: 1.0 (Soft Rock) ~ 10.0 (Hard Cliff)")
    
    if 'control_points' not in st.session_state:
        st.session_state.control_points = pd.DataFrame({
            "Layer": [1, 30],
            "Resistance": [1.0, 1.0],
            "Thickness": [10.0, 10.0]
        })
        
    with st.expander("Design Geological Array", expanded=True):
        
        # Configure columns dynamically based on checkbox
        col_config = {
            "Resistance": st.column_config.NumberColumn("Resistance", min_value=1.0, max_value=10.0, step=0.1)
        }
        
        if not enable_thickness:
            col_config["Thickness"] = None # This effectively hides the column
        else:
            col_config["Thickness"] = st.column_config.NumberColumn("Thickness", min_value=0.1, step=1.0)
            
        edited_df = st.data_editor(st.session_state.control_points, 
                                   num_rows="dynamic", 
                                   hide_index=True,
                                   use_container_width=True,
                                   key='data_editor',
                                   column_config=col_config)
        
        # Clean and process user data
        valid_df = edited_df.dropna(subset=["Layer", "Resistance"]).sort_values(by="Layer").drop_duplicates(subset=["Layer"])
        if len(valid_df) == 0:
            valid_df = pd.DataFrame({"Layer": [1, num_layers], "Resistance": [1.0, 1.0], "Thickness": [10.0, 10.0]})
            
        x_control = valid_df["Layer"].values
        y_res_control = valid_df["Resistance"].values
        
        # Piecewise Linear Interpolation
        x_target = np.arange(1, num_layers + 1)
        y_res_target = np.interp(x_target, x_control, y_res_control)
        resistances_list = y_res_target.tolist()
        
        if enable_thickness and "Thickness" in valid_df.columns and not valid_df["Thickness"].isna().all():
            # If enabled and valid thickness data exists, interpolate it
            y_thi_control = valid_df["Thickness"].fillna(10.0).values
            y_thi_target = np.interp(x_target, x_control, y_thi_control)
            y_thi_target = np.maximum(y_thi_target, 0.1)
            thicknesses_list = y_thi_target.tolist()
        else:
            # If disabled, uniform thickness
            y_thi_target = np.full(num_layers, 10.0)
            thicknesses_list = y_thi_target.tolist()

        # Mini Dual-axis Chart
        fig_curve = make_subplots(specs=[[{"secondary_y": True}]])
        
        if enable_thickness:
            fig_curve.add_trace(go.Bar(
                x=x_target, y=y_thi_target, 
                marker_color='rgba(150, 150, 200, 0.4)', 
                name='Thickness (Relative)'
            ), secondary_y=False)
        
        fig_curve.add_trace(go.Scatter(
            x=x_target, y=y_res_target, mode='lines', 
            line=dict(color='gray', width=2, dash='dot'), 
            name='Res Interpolated'
        ), secondary_y=True)
        
        fig_curve.add_trace(go.Scatter(
            x=x_control, y=y_res_control, mode='markers+lines', 
            marker=dict(color='red', size=10), 
            line=dict(color='#2c3e50', width=3),
            name='Res Control Points'
        ), secondary_y=True)
        
        fig_curve.update_layout(
            height=200, margin=dict(l=0, r=0, t=10, b=0),
            xaxis_title="Layer Number (1 = Bottom)",
            showlegend=False
        )
        if enable_thickness:
            fig_curve.update_yaxes(title_text="Thickness", secondary_y=False, showgrid=False)
        else:
            fig_curve.update_yaxes(visible=False, secondary_y=False) # Hide primary Y if bar isn't there
            
        fig_curve.update_yaxes(title_text="Resistance", secondary_y=True, range=[0, max(10, max(y_res_target)*1.2)])
        
        st.plotly_chart(fig_curve, use_container_width=True)

    st.markdown("#### Dynamic Rates")
    uplift_rate = st.slider("Uplift Rate (mm/year)", min_value=0.0, max_value=2.0, value=0.5, step=0.1)
    incision_rate = st.slider("Global River Incision Rate (mm/year)", min_value=0.0, max_value=4.0, value=1.0, step=0.1)
    
    st.markdown("---")
    generate_clicked = st.button("🔨 Calculate & Generate Animation", type="primary", use_container_width=True)


with col1:
    plot_placeholder = st.empty()
    
# ==========================================
# PRE-COMPUTE FRAMES FOR NATIVE JS ANIMATION
# ==========================================

if generate_clicked:
    with st.spinner("Calculating 100 Frames of Advanced Differential Geomorphology..."):
        frames = []
        MAX_TIME = 10.0
        DT = 0.1
        time_steps = np.arange(0, MAX_TIME + DT, DT)
        x = np.linspace(-1000, 1000, 250) 
        
        engine = SimulationEngine(num_layers, resistances_list, thicknesses_list)
        
        frame_data_snapshots = []
        initial_traces = []
        
        for idx, t in enumerate(time_steps):
            if t > 0:
                engine.step(DT, uplift_rate, incision_rate)
                
            T = engine.get_terrain_profile(x)
            uplift_m = engine.uplift_m
            
            current_traces = []
            
            # Basement First (Index 0)
            current_traces.append(go.Scatter(
                x=np.concatenate([x, x[::-1]]),
                y=np.concatenate([np.zeros_like(x), np.minimum(uplift_m, T)[::-1]]),
                fill='toself', fillcolor="#333333", line=dict(color="rgba(0,0,0,0)"),
                name="Basement Rock (Res: Max)", hoverinfo="skip"
            ))
            
            for layer in reversed(engine.layers):
                layer_bottom = layer.bottom + uplift_m
                layer_top = layer.top + uplift_m
                
                Y_bottom = np.minimum(layer_bottom, T)
                Y_top = np.minimum(layer_top, T)
                
                poly_x = np.concatenate([x, x[::-1]])
                poly_y = np.concatenate([Y_bottom, Y_top[::-1]])
                
                current_traces.append(go.Scatter(
                    x=poly_x, y=poly_y, fill='toself', fillcolor=layer.color,
                    line=dict(color="rgba(0,0,0,0.5)", width=0.5), name=layer.name
                ))
                
            if idx == 0:
                initial_traces = current_traces
                
            layout_override = go.Layout(
                title_text=f"Time Elapsed: {t:.1f} Million Years | V-Notch Depth: {engine.incision_m:.1f} Meters"
            )
            frames.append(go.Frame(data=current_traces, name=str(idx), layout=layout_override))
        
        
        fig = go.Figure(data=initial_traces, frames=frames)
        
        fig.update_layout(
            title_text="Time Elapsed: 0.0 Million Years | V-Notch Depth: 0.0 Meters",
            title_x=0.5,
            xaxis_title="Cross-Section Width (meters)",
            yaxis_title="Elevation (meters)",
            xaxis=dict(range=[-1000, 1000], showgrid=False, zeroline=False),
            yaxis=dict(range=[0, min(3000, 250 + MAX_TIME*uplift_rate*100 + 500)], showgrid=True, gridcolor='lightgrey', zeroline=False),
            showlegend=True,
            legend=dict(yanchor="top", y=1.0, xanchor="left", x=1.02),
            margin=dict(l=40, r=150, t=50, b=40),
            plot_bgcolor="white", height=600,
            updatemenus=[dict(
                type="buttons",
                showactive=False,
                y=0.05, x=0.05,
                xanchor="left", yanchor="bottom",
                buttons=[
                    dict(
                        label="► Play Animation",
                        method="animate",
                        args=[None, {"frame": {"duration": 50, "redraw": False}, "fromcurrent": True, "transition": {"duration": 0}}]
                    ),
                    dict(
                        label="❚❚ Pause",
                        method="animate",
                        args=[[None], {"frame": {"duration": 0, "redraw": False}, "mode": "immediate", "transition": {"duration": 0}}]
                    )
                ]
            )]
        )
        
        sliders = [dict(
            steps=[dict(
                method='animate',
                args=[[str(k)], dict(mode='immediate', frame=dict(duration=0, redraw=False), transition=dict(duration=0))],
                label=f"{time_steps[k]:.1f} Myr"
            ) for k in range(len(frames))],
            active=0,
            transition=dict(duration=0),
            x=0, y=0, currentvalue=dict(font=dict(size=12), prefix="Scrub Time: ", visible=False)
        )]
        
        fig.update_layout(sliders=sliders)
        st.session_state.animated_fig = fig

if "animated_fig" in st.session_state:
    plot_placeholder.plotly_chart(st.session_state.animated_fig, use_container_width=True)
else:
    plot_placeholder.info("⚙️ Set up your Geological Parameters on the right and click **Calculate & Generate Animation** to build exactly 10 million years of physics computation!")
