import streamlit as st
import json
import os
from datetime import datetime
import pandas as pd
from fpdf import FPDF
import arabic_reshaper
from bidi.algorithm import get_display

DATA_FILE = "multi_factory_data.json"

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return {
        "inventory": {
            "الحنفية": 100.0, "البانكة": 50.0, "الماطور": 50.0, "التوماتيك": 50.0,
            "الطواف": 50.0, "الراديتر": 50.0, "زواية القاعدة": 200.0,
            "المنيوم القاعدة 1.35m": 50.0, "الجكنة": 100.0, "واشر حديد": 100.0,
            "واشر بلاستك": 100.0, "زبانة": 100.0, "كبلري 1.7m": 50.0,
            "كويل": 50.0, "بوري ربع 1.5m": 50.0, "طبقة وربع بليت": 1.25
        },
        "agents": {
            "سوران مغديد": {
                "debt": -98070000.0,
                "transactions": []
            }
        },
        "receipt_counter": 1001,
        "sales_history": [],
        "production_history": []
    }

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

st.set_page_config(page_title="إدارة الوكلاء وسديد الديون", layout="wide")
data = load_data()

st.title("🤝 إدارة الوكلاء وتسديد الديون")

tabs = st.tabs(["تسديد دين / استلام دفعة", "إدارة الوكلاء", "المخزون"])

with tabs[0]:
    st.subheader("تسديد مبلغ مال من الوكيل (وصل قبض)")
    
    agents = list(data["agents"].keys())
    if agents:
        selected_ag = st.selectbox("اختر الوكيل:", agents)
        
        current_debt = data["agents"][selected_ag].get("debt", 0.0)
        
        st.markdown(f"""
        <div style="background-color: #3b3a2a; padding: 15px; border-radius: 8px; border: 1px solid #c9b037; margin-bottom: 20px;">
            <span style="font-size: 18px; color: #f1e05a;">💰 الدين الحالي المترتب على الوكيل [{selected_ag}]:</span><br>
            <span style="font-size: 22px; font-weight: bold; color: #fff;">{current_debt:,.1f-} د.ع</span>
        </div>
        """, unsafe_allow_html=True)
        
        pay_amount = st.number_input("المبلغ المدفوع (المستلم):", min_value=0.0, value=abs(current_debt), step=1000.0)
        pay_note = st.text_input("ملاحظات / بيان الدفعة:", value="تسديد دفعة نقداً")
        
        if st.button("💵 تأكيد استلام المبلغ وخصمه من الدين", type="primary", use_container_width=True):
            # التصحيح البرمجي: جمع المبلغ المدفوع (الموجب) مع الدين (السالب) لتقليصه نحو الصفر
            new_debt = current_debt + pay_amount
            data["agents"][selected_ag]["debt"] = new_debt
            
            receipt_no = data.get("receipt_counter", 1001)
            data["receipt_counter"] = receipt_no + 1
            
            data["agents"][selected_ag].setdefault("transactions", []).append({
                "date": datetime.now().strftime("%Y-%m-%d"),
                "type": "تسديد دفعة",
                "amount": pay_amount,
                "balance": new_debt,
                "note": f"وصل قبض #{receipt_no} - {pay_note}"
            })
            
            save_data(data)
            
            st.markdown(f"""
            <div style="background-color: #1e3a2f; padding: 15px; border-radius: 8px; border: 1px solid #2ecc71; margin-top: 20px;">
                <span style="font-size: 18px; color: #2ecc71;">✅ تم خصم المبلغ. الدين المتبقي على الوكيل:</span><br>
                <span style="font-size: 22px; font-weight: bold; color: #fff;">{new_debt:,.1f} د.ع</span>
            </div>
            """, unsafe_allow_html=True)
            st.rerun()
    else:
        st.info("لا يوجد وكلاء مضافون حالياً.")

with tabs[1]:
    st.subheader("إضافة وكيل جديد")
    new_agent_name = st.text_input("اسم الوكيل:")
    initial_debt = st.number_input("الدين الافتتاحي (ضع علامة سالب إذا كان ديناً عليه):", value=0.0)
    if st.button("إضافة الوكيل"):
        if new_agent_name and new_agent_name not in data["agents"]:
            data["agents"][new_agent_name] = {"debt": initial_debt, "transactions": []}
            save_data(data)
            st.success(f"تم إضافة الوكيل {new_agent_name} بنجاح!")
            st.rerun()

with tabs[2]:
    st.subheader("مخزون المعمل")
    df = pd.DataFrame.from_dict(data["inventory"], orient='index', columns=['الكمية'])
    st.dataframe(df, use_container_width=True)
