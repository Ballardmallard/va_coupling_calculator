import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

class VACouplingApp:
    def __init__(self, ef, svr):
        self.ef = ef
        self.svr = svr

    def calculate_sv(self, hr, svr, ef):
        base_edv = 150
        diastolic_time = 60/hr - 0.2
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

st.title("VA Coupling Calculator")

ef = st.slider("Ejection Fraction", 0.15, 0.75, 0.35, 0.01)
svr = st.slider("SVR (dyn⋅s/cm5)", 500, 1700, 800, 10)

if st.button("Plot Results"):
    app = VACouplingApp(ef, svr)
    data = app.generate_data()
    optimal_row = data.loc[data['efficiency'].idxmax()]

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=data['hr'], y=data['efficiency'], mode='lines', name='Efficiency'))
    fig.add_trace(go.Scatter(x=data['hr'], y=data['coupling_ratio'], mode='lines', name='VA Coupling Ratio', yaxis='y2'))

    fig.update_layout(
        title=f"Cardiac Efficiency and VA Coupling (EF={ef*100:.0f}%, SVR={svr})",
        xaxis_title='Heart Rate (bpm)',
        yaxis=dict(title='Efficiency (%)'),
        yaxis2=dict(title='VA Coupling Ratio', overlaying='y', side='right'),
        shapes=[
            dict(
                type='line', x0=optimal_row['hr'], x1=optimal_row['hr'], y0=0, y1=optimal_row['efficiency'],
                line=dict(color='Red', dash='dash')
            )
        ],
        annotations=[
            dict(
                x=optimal_row['hr'], y=optimal_row['efficiency'], text=f"Optimal HR: {optimal_row['hr']:.0f} bpm", showarrow=True
            )
        ]
    )

    st.plotly_chart(fig)
