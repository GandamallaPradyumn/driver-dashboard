from datetime import datetime
import streamlit as st
import pandas as pd
import altair as alt

class Dashboard:

    def __init__(self):
        self.annual_df = pd.read_csv("ANNUAL_DRI_DATA.csv")
        self.monthly_df = pd.read_csv("DRI_DUTY.csv")
        self.lsa_df = pd.read_csv("LSA.csv")

        self.annual_df.columns = self.annual_df.columns.str.upper()
        self.monthly_df.columns = self.monthly_df.columns.str.upper()
        self.lsa_df.columns = self.lsa_df.columns.str.upper()

        self.monthly_df.dropna(subset=['DATE', 'KMS', 'HOURS', 'D/N_OUT'], inplace=True)
        self.monthly_df['DATE'] = pd.to_datetime(self.monthly_df['DATE'], dayfirst=True)
        self.monthly_df['KMS'] = pd.to_numeric(self.monthly_df['KMS'])
        self.monthly_df['HOURS'] = pd.to_numeric(self.monthly_df['HOURS'])
        self.monthly_df['MONTH_YEAR'] = self.monthly_df['DATE'].dt.to_period('M').dt.to_timestamp().dt.strftime('%B %Y')

        self.lsa_df['DATE'] = pd.to_datetime(self.lsa_df['DATE'], dayfirst=True)
        self.lsa_df = self.lsa_df[self.lsa_df['DATE'] < '2024-04-01']
        self.lsa_df['MONTH_YEAR'] = self.lsa_df['DATE'].dt.to_period('M').dt.to_timestamp().dt.strftime('%B %Y')

        self.month_order = pd.date_range(start=self.monthly_df['DATE'].min(), end=self.monthly_df['DATE'].max(), freq='MS').strftime('%B %Y').tolist()
        self.months_order = self.month_order

        self.depots = ['ADB', 'FLK', 'HYD2', 'JGIT', 'KMM', 'KMR', 'MBNR', 'MHBD', 'MLG', 'RNG', 'SRD']
        self.ui()

    def ui(self):
        st.set_page_config(page_title="Driver Dashboard", layout="wide")
        self.driver_view()

    def driver_view(self):
        st.image("LOGO.png", width=80)
        st.markdown("<h1 style='font-size:48px;'>TGSRTC DRIVER PRODUCTIVITY & HEALTH</h1>", unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        selected_depot = col1.selectbox("Select Depot", self.depots)
        self.filtered_df = self.annual_df[self.annual_df['DEPOT'] == selected_depot]
        driver_ids = self.filtered_df['EMP_ID'].unique()
        self.selected_driver = col2.selectbox("Select Driver ID", driver_ids)

        driver_data_row = self.filtered_df[self.filtered_df['EMP_ID'] == self.selected_driver]
        if driver_data_row.empty:
            st.error("Driver not found.")
            return

        driver_data = driver_data_row.iloc[0].copy()
        driver_data['HOURS'] = self.monthly_df[self.monthly_df['EMP_ID'] == self.selected_driver]['HOURS'].sum()
        lsa_count = self.lsa_df[self.lsa_df['EMP_ID'] == self.selected_driver]['LSA'].sum()

        st.markdown(f"<h2 style='font-size:32px;'>Driver: {driver_data['DRIVER_NAME']} (ID: {driver_data['EMP_ID']})</h2>", unsafe_allow_html=True)
        st.markdown(f"<h3 style='font-size:28px;'>Depot: {driver_data['DEPOT']}</h3>", unsafe_allow_html=True)

        col3, col4 = st.columns(2)
        col3.metric("KM Driven", f"{driver_data['KMS_DRIVEN']} km")
        col4.metric("Hours Worked", f"{driver_data['HOURS']} hrs")

        col5, col6 = st.columns(2)
        col5.metric("Leaves Taken", f"{lsa_count} days")
        col6.metric("Health Score", f"{driver_data['HEALTH_SCORE']} Grade")

        self.bar_chart("Monthly KM Driven", "Month-Year", "KMs", self.monthly_df, 'KMS')
        self.bar_chart("Monthly Hours Worked", "Month-Year", "Hours", self.monthly_df, 'HOURS')

        if 'DOUBLE_DUTY' in self.monthly_df.columns:
            self.bar_chart("Double Duties", "Month-Year", "Double Duties", self.monthly_df, 'DOUBLE_DUTY')
        if 'LSA' in self.lsa_df.columns:
            self.bar_chart("Leaves (LSA)", "Month-Year", "Leaves", self.lsa_df, 'LSA')

        self.grp_bar_chart(self.monthly_df)

    def bar_chart(self, title, x_title, y_title, df, value_col):
        df = df[df['EMP_ID'] == self.selected_driver]
        base_df = pd.DataFrame({'MONTH_YEAR': self.months_order})
        summary = df.groupby('MONTH_YEAR', as_index=False)[value_col].sum()
        summary = base_df.merge(summary, on='MONTH_YEAR', how='left')
        summary[value_col] = summary[value_col].fillna(0)
        summary['MONTH_YEAR'] = pd.Categorical(summary['MONTH_YEAR'], categories=self.months_order, ordered=True)
        summary = summary.sort_values('MONTH_YEAR')
        average = summary[value_col].mean()

        theme_color = 'white' if st.get_option("theme.base") == "dark" else 'black'

        chart = alt.Chart(summary).mark_bar(color='#5A00FF').encode(
            x=alt.X('MONTH_YEAR:N', title=x_title),
            y=alt.Y(f"{value_col}:Q", title=y_title),
            tooltip=['MONTH_YEAR', value_col]
        )

        avg_line = alt.Chart(pd.DataFrame({'y': [average]})).mark_rule(
            color='crimson', strokeDash=[6, 4]
        ).encode(y='y:Q')

        text = alt.Chart(summary).mark_text(
            align='center',
            baseline='bottom',
            dy=-8,
            color='white',
            fontSize=14,
            fontWeight='bold'
        ).encode(
            x='MONTH_YEAR:N',
            y=alt.Y(f'{value_col}:Q'),
            text=alt.Text(f'{value_col}:Q', format='.0f')
        )

        st.markdown(f"<h3 style='font-size:28px;'>{title}</h3>", unsafe_allow_html=True)
        st.altair_chart((chart + avg_line + text).properties(width=1000), use_container_width=True)

    def grp_bar_chart(self, df):
        df = df[df['EMP_ID'] == self.selected_driver]
        base_df = pd.DataFrame({'MONTH_YEAR': self.months_order})

        summary_day = df[df['D/N_OUT'] == 'D'].groupby('MONTH_YEAR').size().reset_index(name='Count')
        summary_day = base_df.merge(summary_day, on='MONTH_YEAR', how='left')
        summary_day['Shift'] = 'DAY OUT'

        summary_night = df[df['D/N_OUT'] == 'N'].groupby('MONTH_YEAR').size().reset_index(name='Count')
        summary_night = base_df.merge(summary_night, on='MONTH_YEAR', how='left')
        summary_night['Shift'] = 'NIGHT OUT'

        summary_df = pd.concat([summary_day, summary_night])
        summary_df['Count'] = summary_df['Count'].fillna(0)
        summary_df['MONTH_YEAR'] = pd.Categorical(summary_df['MONTH_YEAR'], categories=self.months_order, ordered=True)
        summary_df = summary_df.sort_values('MONTH_YEAR')

        avg_day = summary_day['Count'].mean()
        avg_night = summary_night['Count'].mean()

        theme_color = 'white' if st.get_option("theme.base") == "dark" else 'black'

        bar_chart = alt.Chart(summary_df).mark_bar().encode(
            x=alt.X('MONTH_YEAR:N', title='Month-Year'),
            y=alt.Y('Count:Q', title='Duties Count'),
            color='Shift:N',
            tooltip=['MONTH_YEAR', 'Shift', 'Count']
        )

        avg_lines = alt.Chart(pd.DataFrame({'y': [avg_day, avg_night], 'Shift': ['DAY OUT', 'NIGHT OUT']})).mark_rule(
            strokeDash=[4, 2]
        ).encode(
            y='y:Q',
            color='Shift:N'
        )

        text = alt.Chart(summary_df).mark_text(
            align='center',
            baseline='bottom',
            dy=-5,
            color='white',
            fontSize=14,
            fontWeight='bold'
        ).encode(
            x='MONTH_YEAR:N',
            y=alt.Y('Count:Q'),
            text=alt.Text('Count:Q', format='.0f')
        )

        st.markdown("<h3 style='font-size:28px;'>Day vs Night Duties</h3>", unsafe_allow_html=True)
        st.altair_chart((bar_chart + avg_lines + text).properties(width=1000), use_container_width=True)

if __name__ == '__main__':
    Dashboard()
