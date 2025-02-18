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

    def calculate_optimal_wedge_pressure(self, hr, svr, ef):
        """
        Dynamically calculate optimal wedge pressure based on complex physiological interactions
        
        Key Principles from Sepsis Hemodynamic Research:
        - Filling pressure is dynamically linked to multiple physiological parameters
        - Optimal pressure varies with cardiac function, heart rate, and vascular resistance
        - Considers both global and regional perfusion dynamics
        """
        # Fundamental physiological parameters
        diastolic_time = 60/hr - 0.2  # Estimated diastolic filling time
        
        # Ejection Fraction Sensitivity
        # Lower EF suggests reduced ventricular compliance and different filling requirements
        ef_factor = 1 - ef  # Ranges from 0 (high EF) to 1 (low EF)
        
        # Systemic Vascular Resistance Impact
        # Higher SVR suggests increased afterload and different filling pressure needs
        svr_factor = (svr / 800 - 1)  # Normalized SVR deviation
        
        # Heart Rate Dynamics
        # Shorter diastolic time may require different filling pressures
        hr_factor = 1 - np.exp(-0.1 * (hr - 75))  # Non-linear heart rate effect
        
        # Global Perfusion Considerations
        # Base calculation with multi-parametric adjustments
        # Incorporates principles from sepsis hemodynamic research
        optimal_wedge = (
            12  # Central reference point
            * (1 - 0.4 * ef_factor)  # EF adjustment (more significant impact)
            * (1 + 0.3 * svr_factor)  # SVR adjustment
            * (1 + 0.2 * hr_factor)  # Heart rate adjustment
        )
        
        # Physiological Constraints
        # Ensure wedge pressure remains in a clinically reasonable range
        return max(5, min(25, optimal_wedge))

    def calculate_venous_congestion(self, hr, svr, ef):
        """
        Calculate venous congestion risk with sophisticated physiological modeling
        
        Principles:
        - Asymmetric penalty function
        - Dynamic optimal wedge pressure
        - Sensitivity to multiple physiological parameters
        """
        # Dynamically calculate optimal wedge pressure
        optimal_wedge = self.calculate_optimal_wedge_pressure(hr, svr, ef)
        
        # Sensitivity factors
        # More significant impact for lower EF and higher SVR
        ef_sensitivity = 1.5 - ef  # Lower EF increases sensitivity
        svr_sensitivity = svr / 800  # Higher SVR increases sensitivity
        overall_sensitivity = ef_sensitivity * svr_sensitivity
        
        def congestion_penalty(wedge):
            """
            Advanced congestion penalty calculation
            
            Key Features:
            - Asymmetric response to filling pressure deviation
            - More lenient for low pressures
            - Steeper penalty for high pressures
            - Dynamically adjusted by physiological parameters
            """
            # Calculate deviation from optimal
            deviation = wedge - optimal_wedge
            
            # Asymmetric penalty with non-linear scaling
            if deviation < 0:
                # More lenient for low filling pressures
                # Quadratic penalty with reduced slope
                penalty = (deviation ** 2) * 0.3
            else:
                # Steeper, non-linear penalty for high filling pressures
                # Exponential-like increase
                penalty = np.exp(deviation) - 1
            
            # Scale penalty by sensitivity factors
            return penalty * overall_sensitivity
        
        return congestion_penalty, optimal_wedge

    def calculate_efficiency(self, hr, svr, ef):
        ea, ees, sv, map_pressure = self.calculate_elastances(hr, svr, ef)
        
        # Calculate coupling ratio
        coupling_ratio = ea/ees
        
        # Calculate venous congestion penalty and optimal wedge pressure
        congestion_func, optimal_wedge = self.calculate_venous_congestion(hr, svr, ef)
        
        # Calculate congestion penalty at the optimal wedge pressure
        congestion_penalty = congestion_func(optimal_wedge)
        
        # Mechanical efficiency calculation
        mechanical_efficiency = np.exp(-((coupling_ratio - 0.8)/0.4)**2)
        
        # Diastolic efficiency calculation
        diastolic_efficiency = np.exp(-0.5 * ((hr - 75)/30)**2)
        
        # Final efficiency with congestion penalty
        efficiency = mechanical_efficiency * diastolic_efficiency * (1 - congestion_penalty) * 100
        
        return efficiency, coupling_ratio, sv, (sv * hr) / 1000, optimal_wedge

    def generate_data(self):
        hrs = np.linspace(40, 120, 81)
        
        data = []
        for hr in hrs:
            eff, coup, sv, co, optimal_wedge = self.calculate_efficiency(hr, self.svr, self.ef)
            data.append({
                'hr': hr,
                'efficiency': eff,
                'coupling_ratio': coup,
                'sv': sv,
                'co': co,
                'optimal_wedge': optimal_wedge
            })
        
        return pd.DataFrame(data)

def main():
    st.title("Ideal Heart Rate for Cardiac Efficiency Based on Minimizing Mechanical Transfer of Power")
    
    st.markdown("""
    ### Cardiovascular Performance and Venous Congestion
    
    This advanced model integrates:
    - Ventricular-Arterial Coupling
    - Systemic Venous Congestion Dynamics
    - Ejection Fraction Sensitivity
    - Systemic Vascular Resistance Impact
    """)

    # Sidebar for parameter inputs
    st.sidebar.header("Input Parameters")
    ef = st.sidebar.slider(
        "Ejection Fraction", 
        min_value=0.05, 
        max_value=0.75, 
        value=0.35, 
        step=0.01,
        help="Percentage of blood volume ejected from the left ventricle"
    )
    svr = st.sidebar.slider(
        "Systemic Vascular Resistance (dyn⋅s/cm5)", 
        min_value=500, 
        max_value=2000, 
        value=800, 
        step=10,
        help="Resistance to blood flow in the systemic circulation"
    )

    # Plot button
    if st.sidebar.button("Generate Analysis"):
        # Create app instance
        app = VACouplingApp(ef, svr)
        
        # Generate data
        data = app.generate_data()
        
        # Find optimal parameters
        optimal_row = data.loc[data['efficiency'].idxmax()]
        
        # Create Plotly figures
        fig1 = go.Figure()
        fig2 = go.Figure()
        
        # Add efficiency trace
        fig1.add_trace(go.Scatter(
            x=data['hr'], 
            y=data['efficiency'], 
            mode='lines', 
            name='Cardiac Efficiency',
            line=dict(color='blue', width=2)
        ))
        
        # Add optimal wedge pressure trace
        fig2.add_trace(go.Scatter(
            x=data['hr'], 
            y=data['optimal_wedge'], 
            mode='lines', 
            name='Optimal Wedge Pressure',
            line=dict(color='green', width=2)
        ))
        
        # Add coupling ratio trace to efficiency plot
        fig1.add_trace(go.Scatter(
            x=data['hr'], 
            y=data['coupling_ratio'], 
            mode='lines', 
            name='VA Coupling Ratio', 
            yaxis='y2',
            line=dict(color='red', width=2)
        ))
        
        # Update efficiency plot layout
        fig1.update_layout(
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
            height=400,
            hovermode='x'
        )
        
        # Update optimal wedge pressure plot layout
        fig2.update_layout(
            title=f"Dynamic Optimal Wedge Pressure (EF={ef*100:.0f}%, SVR={svr})",
            xaxis_title='Heart Rate (bpm)',
            yaxis_title='Optimal Wedge Pressure (mmHg)',
            yaxis=dict(range=[5, 25]),
            height=400,
            hovermode='x'
        )
        
        # Add vertical line for optimal point on efficiency plot
        fig1.add_shape(
            type='line', 
            x0=optimal_row['hr'], 
            x1=optimal_row['hr'], 
            y0=0, 
            y1=optimal_row['efficiency'],
            line=dict(color='Red', dash='dash')
        )
        
        # Add annotation for optimal point on efficiency plot
        fig1.add_annotation(
            x=optimal_row['hr'], 
            y=optimal_row['efficiency'], 
            text=f"Optimal HR: {optimal_row['hr']:.0f} bpm<br>Max Efficiency: {optimal_row['efficiency']:.1f}%",
            showarrow=True,
            arrowhead=2,
            arrowsize=1,
            arrowwidth=2,
            arrowcolor="#636363"
        )
        
        # Display the plots
        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(fig1, use_container_width=True)
        with col2:
            st.plotly_chart(fig2, use_container_width=True)
        
        # Display key metrics
        col1, col2, col3 = st.columns(3)
        col1.metric("Optimal Heart Rate", f"{optimal_row['hr']:.0f} bpm")
        col2.metric("Max Efficiency", f"{optimal_row['efficiency']:.1f}%")
        col3.metric("Optimal Wedge Pressure", f"{optimal_row['optimal_wedge']:.1f} mmHg")

        

if __name__ == "__main__":
    main()
