import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go

class VACouplingApp:
    def __init__(self, ef, svr):
        self.ef = ef
        self.svr = svr

    def calculate_sv(self, hr, svr, ef):
        base_edv = 150
        filling_effect = np.exp(-0.25 * np.maximum(0, (hr - 60)/60))
        afterload_effect = np.exp(-0.0003 * (svr - 800))
        edv = base_edv * filling_effect * afterload_effect
        return edv * ef

    def calculate_elastances(self, hr, svr, ef):
        sv = self.calculate_sv(hr, svr, ef)
        co = (sv * hr) / 1000
        map_pressure = (co * svr) / 80
        ea = (map_pressure * 0.9) / sv
        base_ees = 2.0 * ef / 0.55
        ees = base_ees * np.exp(-0.0002 * (svr - 800))
        return ea, ees, sv, map_pressure

    def calculate_efficiency(self, hr, svr, ef):
        ea, ees, sv, map_pressure = self.calculate_elastances(hr, svr, ef)
        coupling_ratio = ea/ees
        mechanical_efficiency = np.exp(-((coupling_ratio - 0.8)/0.4)**2)
        diastolic_efficiency = np.exp(-0.5 * ((hr - 75)/30)**2)
        efficiency = mechanical_efficiency * diastolic_efficiency * 100
        return efficiency, coupling_ratio, sv, (sv * hr) / 1000

    def generate_data(self):
        hrs = np.linspace(40, 120, 81)
        
        data = []
        for hr in hrs:
            eff, coup, sv, co = self.calculate_efficiency(hr, self.svr, self.ef)
            data.append({
                'hr': hr,
                'efficiency': eff,
                'coupling_ratio': coup,
                'sv': sv,
                'co': co
            })
        return pd.DataFrame(data)

def main():
    st.title("VA Coupling Calculator")

    # Sidebar for input parameters
    st.sidebar.header("Input Parameters")
    ef = st.sidebar.slider(
        "Ejection Fraction", 
        min_value=0.15, 
        max_value=0.75, 
        value=0.35, 
        step=0.01,
        help="Percentage of blood volume ejected from the left ventricle"
    )
    svr = st.sidebar.slider(
        "Systemic Vascular Resistance (dyn⋅s/cm5)", 
        min_value=500, 
        max_value=1700, 
        value=800, 
        step=10,
        help="Resistance to blood flow in the systemic circulation"
    )

    # Plot button
    if st.sidebar.button("Calculate and Plot"):
        # Create app instance
        app = VACouplingApp(ef, svr)
        
        # Generate data
        data = app.generate_data()
        
        # Find optimal parameters
        optimal_row = data.loc[data['efficiency'].idxmax()]
        
        # Create Plotly figure
        fig = go.Figure()
        
        # Add efficiency trace
        fig.add_trace(go.Scatter(
            x=data['hr'], 
            y=data['efficiency'], 
            mode='lines', 
            name='Cardiac Efficiency',
            line=dict(color='blue', width=2)
        ))
        
        # Add coupling ratio trace
        fig.add_trace(go.Scatter(
            x=data['hr'], 
            y=data['coupling_ratio'], 
            mode='lines', 
            name='VA Coupling Ratio', 
            yaxis='y2',
            line=dict(color='red', width=2)
        ))
        
        # Update layout
        fig.update_layout(
            title=f"Cardiac Efficiency and VA Coupling (EF={ef*100:.0f}%, SVR={svr})",
            xaxis_title='Heart Rate (bpm)',
            yaxis=dict(
                title='Efficiency (%)', 
                range=[0, 100]
            ),
            yaxis2=dict(
                title='VA Coupling Ratio', 
                overlaying='y', 
                side='right',
                range=[0, 3]
            ),
            height=600,
            hovermode='x'
        )
        
        # Add vertical line for optimal point
        fig.add_shape(
            type='line', 
            x0=optimal_row['hr'], 
            x1=optimal_row['hr'], 
            y0=0, 
            y1=optimal_row['efficiency'],
            line=dict(color='Red', dash='dash')
        )
        
        # Add annotation for optimal point
        fig.add_annotation(
            x=optimal_row['hr'], 
            y=optimal_row['efficiency'], 
            text=f"Optimal HR: {optimal_row['hr']:.0f} bpm", 
            showarrow=True
        )
        
        # Display the plot
        st.plotly_chart(fig, use_container_width=True)
        
        # Display key metrics
        col1, col2, col3 = st.columns(3)
        col1.metric("Optimal Heart Rate", f"{optimal_row['hr']:.0f} bpm")
        col2.metric("Max Efficiency", f"{optimal_row['efficiency']:.1f}%")
        col3.metric("VA Coupling Ratio", f"{optimal_row['coupling_ratio']:.2f}")

if __name__ == "__main__":
    main()
