import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="דשבורד משימות מודל - מחוז ירושלים", layout="wide", page_icon="🏆")

def safe_read_csv(filename):
    encodings = ['utf-8-sig', 'cp1255', 'iso-8859-8']
    for enc in encodings:
        try:
            return pd.read_csv(filename, encoding=enc)
        except Exception:
            continue
    return pd.DataFrame()

@st.cache_data
def load_and_process_data():
    # 1. טעינת קובץ ההחרגות
    excluded_df = safe_read_csv('מוסדות_להחרגה.csv')
    if not excluded_df.empty and len(excluded_df.columns) > 0:
        col_ex = 'סמל מוסד' if 'סמל מוסד' in excluded_df.columns else excluded_df.columns[0]
        excluded_ids = excluded_df[col_ex].astype(str).str.replace(r'\.0$', '', regex=True).str.strip().tolist()
    else:
        excluded_ids = []

    # 2. עיבוד קבצי המודל - חילוץ סמל המוסד מתוך עמודת "מוסד"
    def process_moodle_file(filename, domain):
        df = safe_read_csv(filename)
        if df.empty: return df
        
        df = df.iloc[1:].reset_index(drop=True)
        df.columns = df.columns.str.strip()
        
        if 'מוסד' in df.columns:
            # התיקון הקריטי: שולף את המספר שלפני המקף!
            df['סמל מוסד'] = df['מוסד'].astype(str).str.split('-').str[0].str.strip()
        else:
            return pd.DataFrame()
            
        col_district = 'מחוז תקשוב' if 'מחוז תקשוב' in df.columns else df.columns[2]
        col_supervisor = 'שם מפקח' if 'שם מפקח' in df.columns else df.columns[4]
        col_avg = 'ממוצע משימות לתלמיד' if 'ממוצע משימות לתלמיד' in df.columns else df.columns[10]
        
        df['ממוצע משימות'] = pd.to_numeric(df[col_avg], errors='coerce').fillna(0).round(2)
        df['תחום'] = domain
        
        df = df.rename(columns={col_district: 'מחוז תקשוב', col_supervisor: 'שם מפקח'})
        df = df[~df['סמל מוסד'].isin(excluded_ids)]
        return df

    df_math = process_moodle_file('מתמטיקה מודל.csv', 'מתמטיקה')
    df_sci = process_moodle_file('מדעים מודל.csv', 'מדעים')
    
    frames = [df for df in [df_math, df_sci] if not df.empty]
    df1 = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    
    # 3. קובץ ללא קורסים
    try:
        df2 = pd.read_excel('ללא קורסים.csv.xlsx', engine='openpyxl')
    except:
        df2 = safe_read_csv('ללא קורסים.csv.xlsx')
            
    if not df2.empty:
        df2.columns = df2.columns.str.strip()
        if 'מוסד' in df2.columns:
            df2['סמל מוסד'] = df2['מוסד'].astype(str).str.split('-').str[0].str.strip()
            df2 = df2[~df2['סמל מוסד'].isin(excluded_ids)]
            
        col_district2 = 'מחוז' if 'מחוז' in df2.columns else ('מחוז תקשוב' if 'מחוז תקשוב' in df2.columns else '')
        col_supervisor2 = 'מפקח' if 'מפקח' in df2.columns else ('שם מפקח' if 'שם מפקח' in df2.columns else '')
        
        if col_district2: df2 = df2.rename(columns={col_district2: 'מחוז תקשוב'})
        if col_supervisor2: df2 = df2.rename(columns={col_supervisor2: 'שם מפקח'})
        
        df2['תחום'] = 'כללי'
        
    return df1, df2

df1, df2 = load_and_process_data()

st.title("🏆 דשבורד משימות מודל - מחוז ירושלים")
st.markdown("### 🎯 יעד לחודש מרץ: 95% ביצוע | 17 משימות במתמטיקה | 8 משימות במדעים")
st.divider()

if df1.empty:
    st.error("הנתונים מקבצי מתמטיקה/מדעים עדיין לא נטענו. אנא ודאי שהם ב-GitHub.")
    st.stop()

district_list = [d for d in df1['מחוז תקשוב'].dropna().unique() if str(d).strip() != '']
district = st.sidebar.selectbox("בחר/י מחוז למיקוד:", district_list) if district_list else ""

if not district:
    st.stop()

df1_dist = df1[df1['מחוז תקשוב'] == district]
df2_dist = df2[df2['מחוז תקשוב'] == district] if not df2.empty and 'מחוז תקשוב' in df2.columns else pd.DataFrame()

st.header(f"📌 תמונת מצב - מחוז {district}")

col1, col2 = st.columns(2)
with col1:
    st.subheader("📐 מתמטיקה")
    math_avg = df1_dist[df1_dist['תחום'] == 'מתמטיקה']['ממוצע משימות'].mean()
    st.metric("ממוצע משימות לשכבה", f"{math_avg:.1f}" if pd.notna(math_avg) else "0.0")

with col2:
    st.subheader("🔬 מדעים")
    sci_avg = df1_dist[df1_dist['תחום'] == 'מדעים']['ממוצע משימות'].mean()
    st.metric("ממוצע משימות לשכבה", f"{sci_avg:.1f}" if pd.notna(sci_avg) else "0.0")

st.divider()

st.header("👥 פילוח לפי מפקחים")
if 'שם מפקח' in df1_dist.columns:
    supervisors = sorted([s for s in df1_dist['שם מפקח'].dropna().unique() if str(s).strip() != ''])
    supervisor = st.selectbox("בחר/י מפקח להצגת נתונים:", supervisors) if supervisors else ""
else:
    supervisor = ""

if supervisor:
    df1_sup = df1_dist[df1_dist['שם מפקח'] == supervisor]
    
    chart_data = df1_sup.groupby('תחום')['ממוצע משימות'].mean().reset_index()
    fig = px.bar(chart_data, x='תחום', y='ממוצע משימות', color='תחום', 
                 title=f"ממוצע משימות תחת המפקח/ת: {supervisor}", text_auto='.1f')
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("### 📋 פירוט מוסדות (שיטת הרמזור)")
    
    def style_row(row, domain):
        val = row['ממוצע משימות']
        if pd.isna(val): color = ''
        elif domain == 'מתמטיקה':
            if val < 5: color = 'background-color: #ffcccc; color: black;'
            elif val < 12: color = 'background-color: #ffffcc; color: black;'
            else: color = 'background-color: #ccffcc; color: black;'
        else:
            if val < 2: color = 'background-color: #ffcccc; color: black;'
            elif val < 6: color = 'background-color: #ffffcc; color: black;'
            else: color = 'background-color: #ccffcc; color: black;'
        return [color if col in ['מוסד', 'ממוצע משימות'] else '' for col in row.index]

    cols_to_show = ['סמל מוסד', 'מוסד', 'ממוצע משימות']
    
    tab1, tab2 = st.tabs(["📐 בתי ספר - מתמטיקה", "🔬 בתי ספר - מדעים"])
    
    with tab1:
        df_math_sup = df1_sup[df1_sup['תחום'] == 'מתמטיקה']
        if not df_math_sup.empty:
            st.dataframe(df_math_sup[cols_to_show].style.apply(style_row, domain='מתמטיקה', axis=1), use_container_width=True, hide_index=True)
        
    with tab2:
        df_sci_sup = df1_sup[df1_sup['תחום'] == 'מדעים']
        if not df_sci_sup.empty:
            st.dataframe(df_sci_sup[cols_to_show].style.apply(style_row, domain='מדעים', axis=1), use_container_width=True, hide_index=True)

    st.divider()

    st.header("🚨 מוקדי התערבות דחופים (בתי ספר ללא קורסים)")
    
    if not df2_dist.empty and 'שם מפקח' in df2_dist.columns:
        df2_sup = df2_dist[df2_dist['שם מפקח'] == supervisor] 
        
        if not df2_sup.empty:
            st.warning(f"המפקח/ת {supervisor} אחראי/ת על {len(df2_sup)} מוסדות שטרם פתחו קורסי מודל.")
            if 'מוסד' in df2_sup.columns and 'סמל מוסד' in df2_sup.columns:
                st.dataframe(df2_sup[['סמל מוסד', 'מוסד']], hide_index=True, use_container_width=True)
        else:
            st.success("אין בתי ספר ללא קורסים תחת מפקח זה. עבודה מצוינת!")
    else:
        st.info("אין נתונים זמינים על בתי ספר ללא קורסים למחוז/מפקח זה.")
