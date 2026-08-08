# 2. بيع البرادات
with tabs[1]:
    st.write("### 🛒 تسجيل بيع براد")
    
    # الحصول على البرادات الجاهزة التي كميتها أكبر من 0
    available_goods = {model: qty for model, qty in factory_data["finished_goods"].items() if qty > 0}
    
    if not available_goods:
        st.warning("لا توجد برادات جاهزة للبيع حالياً.")
    else:
        # قائمة منسدلة لاختيار البراد
        selected_model = st.selectbox("اختر البراد:", list(available_goods.keys()))
        
        # اختيار الكمية
        max_qty = available_goods[selected_model]
        qty_to_sell = st.number_input(f"الكمية (المتوفر {max_qty}):", min_value=1, max_value=max_qty, value=1)
        
        if st.button("✅ إتمام عملية البيع"):
            # خصم الكمية من الجاهز
            factory_data["finished_goods"][selected_model] -= qty_to_sell
            
            # تسجيل العملية في التاريخ (Sales History)
            new_sale = {
                "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "item": selected_model,
                "qty": qty_to_sell,
                "total": 0 # يمكنك إضافة حقل للسعر هنا لاحقاً
            }
            factory_data.setdefault("sales_history", []).append(new_sale)
            
            save_all_factories(all_factories)
            st.success(f"تم بيع {qty_to_sell} من {selected_model} بنجاح!")
            st.rerun()
