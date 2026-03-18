import streamlit as st
import pandas as pd
import plotly.express as px

# הגדרת דף בסיסית
st.set_page_config(page_title="דשבורד משימות מודל - מחוז ירושלים", layout="wide", page_icon="🏆")

# פונקציית עזר לקריאת קבצים (מנסה כמה קידודים)
def safe_read_csv(filename):
    encodings = ['utf-8-sig', 'cp1255', 'iso-8859-8']
    for enc in encodings:
        try:
            return pd.read_csv(filename, encoding=enc)
        except Exception:
            continue
    st.error(f"לא הצלחתי לקרוא את הקובץ {filename}. ודאי שזה קובץ CSV תקין.")
    return pd.DataFrame()

# טעינת נתונים ועיבוד גלובלי (לא תלוי במיקום עמודות)
@st.cache_data
def load_and_process_data():
    # 1. טעינת קובץ ההחרגות (לפי סמל מוסד)
    excluded_df = safe_read_csv('מוסדות_להחרגה.csv')
    if not excluded_df.empty and 'סמל מוסד' in excluded_df.columns:
        excluded_ids = excluded_df['סמל מוסד'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip().tolist()
    else:
        excluded_ids = []

    # 2. פונקציית עיבוד לקבצי המודל (מתמטיקה/מדעים)
    def process_moodle_file(filename, domain):
        df = safe_read_csv(filename)
        if df.empty: return df
        
        # ניקוי בסיסי
        df = df.iloc[1:].reset_index(drop=True) # מחיקת שורה 2 המיותרת
        df.columns = df.columns.str.strip() # ניקוי רווחים משמות העמודות
        
        # איתור עמודות קריטיות לפי שם (לא לפי מיקום)
        try:
            col_id = next(c for c in df.columns if 'סמל מוסד' in c)
            col_school = next(c for c in df.columns if 'מוסד' in c and 'סמל' not in c)
            col_district = next(c for c in df.columns if 'מחוז תקשוב' in c)
            col_supervisor = next(c for c in df.columns if 'שם מפקח' in c)
            col_avg = next(c for c in df.columns if 'ממוצע משימות לתלמיד' in c)
        except StopIteration:
            st.error(f"בקובץ {filename} חסרות עמודות קריטיות (כמו סמל מוסד או ממוצע משימות).")
            return pd.DataFrame()

        # הפיכת עמודת ממוצע למספר
        df[col_avg] = pd.to_numeric(df[col_avg], errors='coerce').fillna(0).round(2)
        
        # הוספת עמודת תחום (מתמטיקה/מדעים)
        df['תחום'] = domain
        
        # שינוי שמות העמודות לשמות קבועים לטובת הדשבורד
        df = df.rename(columns={
            col_id: 'סמל מוסד',
            col_school: 'מוסד',
            col_district: 'מחוז תקשוב',
            col_supervisor: 'שם מפקח',
            col_avg: 'ממוצע משימות'
        })
        
        # סינון החרגות לפי סמל מוסד
        df['סמל מוסד_לסינון'] = df['סמל מוסד'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
        df = df[~df['סמל מוסד_לסינון'].isin(excluded_ids)]
        df = df.drop(columns=['סמל מוסד_לסינון'])
            
        return df

    # 3. הפעלת הרובוט על הקבצים
    df_math = process_moodle_file('מתמטיקה מודל.csv', 'מתמטיקה')
    df_sci = process_moodle_file('מדעים מודל.csv', 'מדעים')
    
    # חיבור הקבצים
    frames = [df for df in [df_math, df_sci] if not df.empty]
    df1 = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    
    # 4. טיפול בקובץ "ללא קורסים"
    # הערה: הקובץ המקורי הוא XLSX, אז אנחנו משתמשים בפונקציה אחרת
    try:
        df2 = pd.read_excel('ללא קורסים.csv.xlsx', engine='openpyxl')
    except Exception:
        # ניסיון אחרון למקרה שזה בכל זאת CSV
        df2 = safe_read_csv('ללא קורסים.csv.xlsx')

    if not df2.empty:
        # ניקוי בסיסי של עמודות
        df2.columns = df2.columns.str.strip()
        
        # איתור עמודות קריטיות ב"ללא קורסים"
        try:
            col_id2 = next(c for c in df2.columns if 'סמל מוסד' in c)
            col_school2 = next(c for c in df2.columns if 'מוסד' in c and 'סמל' not in c)
            col_district2 = next(c for c in df2.columns if 'מחוז תקשוב' in c)
            col_supervisor2 = next(c for c in df2.columns if 'מפקח' in c and 'שם' not in c)
        except StopIteration:
            df2 = pd.DataFrame() # אם אין עמודות קריטיות, נתייחס לזה כקובץ ריק
        
        if not df2.empty:
            # שינוי שמות לעמודות קבועות
            df2 = df2.rename(columns={
                col_id2: 'סמל מוסד',
                col_school2: 'מוסד',
                col_district2: 'מחוז תקשוב',
                col_supervisor2: 'שם מפקח'
            })
            
            # מחיקת מוחרגים מקובץ ללא קורסים
            df2['סמל מוסד_לסינון'] = df2['סמל מוסד'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
            df2 = df2[~df2['סמל מוסד_לסינון'].isin(excluded_ids)]
            df2 = df2.drop(columns=['סמל מוסד_לסינון'])
            
            # הערה אסטרטגית: בקובץ שקיבלתי אין עמודת "תחום".
            # כדי שהדשבורד יעבוד, אנחנו "מניחים" שכל בתי הספר האלה הם ללא קורסים במתמטיקה (למשל).
            df2['תחום'] = 'כללי'
            
            # ניקוי רווחים משמות מפקחים ומחוזות
            for col in ['מחוז תקשוב', 'שם מפקח']:
                if col in df2.columns: df2[col] = df2[col].astype(str).str.strip()
                
    return df1, df2

df1, df2 = load_and_process_data()

# כותרת ראשית ותת-כותרת אסטרטגית
st.title("🏆 דשבורד משימות מודל - מחוז ירושלים")
st.markdown("### 🎯 יעד לחודש מרץ: 95% ביצוע | 17 משימות במתמטיקה | 8 משימות במדעים")
st.divider()

# בחירת מחוז בצד
st.sidebar.header("הגדרות תצוגה")
if not df1.empty:
    district_list = df1['מחוז תקשוב'].dropna().unique().tolist()
    district = st.sidebar.selectbox("בחר/י מחוז למיקוד:", district_list)
else:
    district = ""

if not district:
    st.warning("הנתונים חסרים או לא נטענו כראוי. אנא בדקי את השגיאות ב-GitHub.")
    st.stop()

# סינון לפי מחוז
df1_dist = df1[df1['מחוז תקשוב'] == district]
df2_dist = df2[df2['מחוז תקשוב'] == district] if not df2.empty else pd.DataFrame()

# 📌 תמונת מצב מחוזית
st.header(f"📌 תמונת מצב - מחוז {district}")

col1, col2 = st.columns(2)
with col1:
    st.subheader("📐 מתמטיקה")
    math_avg = df1_dist[df1_dist['תחום'] == 'מתמטיקה']['ממוצע משימות'].mean()
    st.metric("ממוצע משימות לשכבה", f"{math_avg:.1f}")

with col2:
    st.subheader("🔬 מדעים")
    sci_avg = df1_dist[df1_dist['תחום'] == 'מדעים']['ממוצע משימות'].mean()
    st.metric("ממוצע משימות לשכבה", f"{sci_avg:.1f}")

st.divider()

# 👥 פילוח לפי מפקחים
st.header("👥 פילוח לפי מפקחים")
if 'שם מפקח' in df1_dist.columns:
    supervisors = df1_dist['שם מפקח'].dropna().unique()
    supervisor = st.selectbox("בחר/י מפקח להצגת נתונים:", supervisors)
else:
    supervisor = ""

if supervisor:
    df1_sup = df1_dist[df1_dist['שם מפקח'] == supervisor]
    
    # גרף עמודות השוואתי (מתמטיקה מול מדעים)
    chart_data = df1_sup.groupby('תחום')['ממוצע משימות'].mean().reset_index()
    fig = px.bar(chart_data, x='תחום', y='ממוצע משימות', color='תחום', 
                 title=f"ממוצע משימות תחת המפקח/ת: {supervisor}", text_auto='.1f')
    st.plotly_chart(fig, use_container_width=True)

    # 📋 פירוט מוסדות (Drill-Down)
    st.markdown("### 📋 פירוט מוסדות (שיטת הרמזור)")
    
    # פונקציית עיצוב צבעונית (רמזור)
    def style_row(row, domain):
        val = row['ממוצע משימות']
        if pd.isna(val): color = ''
        # חוקי צבעים לפי מתמטיקה (17) ומדעים (8)
        elif domain == 'מתמטיקה':
            if val < 5: color = 'background-color: #ffcccc; color: black;' # אדום
            elif val < 12: color = 'background-color: #ffffcc; color: black;' # צהוב
            else: color = 'background-color: #ccffcc; color: black;' # ירוק
        else: # מדעים
            if val < 2: color = 'background-color: #ffcccc; color: black;' # אדום
            elif val < 6: color = 'background-color: #ffffcc; color: black;' # צהוב
            else: color = 'background-color: #ccffcc; color: black;' # ירוק
        
        return [color if col in ['מוסד', 'ממוצע משימות'] else '' for col in row.index]

    cols_to_show = ['סמל מוסד', 'מוסד', 'ממוצע משימות']
    
    tab1, tab2 = st.tabs(["📐 בתי ספר - מתמטיקה", "🔬 בתי ספר - מדעים"])
    
    with tab1:
        df_math_sup = df1_sup[df1_sup['תחום'] == 'מתמטיקה'][cols_to_show]
        st.dataframe(df_math_sup.style.apply(style_row, domain='מתמטיקה', axis=1), use_container_width=True, hide_index=True)
        
    with tab2:
        df_sci_sup = df1_sup[df1_sup['תחום'] == 'מדעים'][cols_to_show]
        st.dataframe(df_sci_sup.style.apply(style_row, domain='מדעים', axis=1), use_container_width=True, hide_index=True)

    st.divider()

    # 🚨 חסימות ומוקדי התערבות (ללא קורסים)
    # הערה אסטרטגית: זהו מוקד הכוח של הדוח. כאן המנכ"ל רואה מי לא התחיל לעבוד.
    st.header("🚨 מוקדי התערבות דחופים (בתי ספר ללא קורסים)")
    
    if not df2_dist.empty and 'שם מפקח' in df2_dist.columns:
        df2_sup = df2_dist[df2_dist['שם מפקח'] == supervisor] 
        
        if not df2_sup.empty:
            st.warning(f"המפקח/ת {supervisor} אחראי/ת על {len(df2_sup)} מוסדות שטרם פתחו קורסי מודל.")
            st.dataframe(df2_sup[['סמל מוסד', 'מוסד']], hide_index=True, use_container_width=True)
        else:
            st.success("אין בתי ספר ללא קורסים תחת מפקח זה. עבודה מצוינת!")
    else:
        st.info("קובץ 'ללא קורסים' חסר או לא תקין. לא ניתן להציג מוקדי התערבות.")
