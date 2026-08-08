# --- تبويب [4]: التحويل بين الدينار والدولار للوكيل ---
tab_convert = tabs[3] if st.session_state.role == "admin" else tabs[2]
with tab_convert:
    st.header("🔄 التحويل والمقاصة بين الدينار العراقي والدولار")

    if not factory_data["agents"]:
        st.warning("لا يوجد وكلاء مسجلون بالنظام.")
    else:
        ex_rate = factory_data.get("exchange_rate", 150000.0)
        st.info(f"💡 سعر الصرف المعتمد في النظام حالياً: **100$ = {ex_rate:,.0f} دينار عراقي**")

        col_c1, col_c2 = st.columns(2)
        with col_c1:
            agent_conv = st.selectbox("اختر الوكيل إجراء التحويل لحسابه:", list(factory_data["agents"].keys()), key="conv_agent_select")
            ag_iqd = factory_data["agents"][agent_conv].get("balance_iqd", 0.0)
            ag_usd = factory_data["agents"][agent_conv].get("balance_usd", 0.0)

            st.write(f"📌 دينار عراقي حالي ذمة الوكيل: **{ag_iqd:,.0f} د.ع**")
            st.write(f"📌 دولار أمريكي حالي ذمة الوكيل: **${ag_usd:,.2f}**")

        with col_c2:
            conv_direction = st.radio(
                "اتجاه التحويل/المقاصة:",
                ["تحويل جزء من الدين من ($USD) إلى (د.ع)", "تحويل جزء من الدين من (د.ع) إلى ($USD)"],
                key="conv_dir"
            )

            if "إلى (د.ع)" in conv_direction:
                if ag_usd <= 0:
                    st.warning("⚠️ هذا الوكيل ليس عليه ديون بالدولار للتحويل منها.")
                    amount_usd_to_convert = 0.0
                    equivalent_iqd = 0.0
                else:
                    default_usd = min(100.0, float(ag_usd))
                    amount_usd_to_convert = st.number_input(
                        "المبلغ المطلوب تحويله بالدولار ($USD):",
                        min_value=0.01,
                        max_value=float(ag_usd),
                        value=float(default_usd),
                        step=10.0
                    )
                    equivalent_iqd = amount_usd_to_convert * (ex_rate / 100.0)
                    st.success(f"المبلغ المعادل بالدينار العراقي: **{equivalent_iqd:,.0f} د.ع**")
            else:
                if ag_iqd <= 0:
                    st.warning("⚠️ هذا الوكيل ليس عليه ديون بالدينار للتحويل منها.")
                    amount_iqd_to_convert = 0.0
                    equivalent_usd = 0.0
                else:
                    default_iqd = min(150000.0, float(ag_iqd))
                    amount_iqd_to_convert = st.number_input(
                        "المبلغ المطلوب تحويله بالدينار (د.ع):",
                        min_value=250.0,
                        max_value=float(ag_iqd),
                        value=float(default_iqd),
                        step=25000.0
                    )
                    equivalent_usd = amount_iqd_to_convert / (ex_rate / 100.0)
                    st.success(f"المبلغ المعادل بالدولار الأمريكي: **${equivalent_usd:,.2f}**")

        if st.button("⚡ إجراء التحويل وتحديث الأرصدة", type="primary", use_container_width=True):
            if "إلى (د.ع)" in conv_direction:
                if amount_usd_to_convert <= 0:
                    st.error("لا يمكن إجراء تحويل بمبلغ 0!")
                else:
                    factory_data["agents"][agent_conv]["balance_usd"] -= amount_usd_to_convert
                    factory_data["agents"][agent_conv]["balance_iqd"] += equivalent_iqd

                    factory_data["agent_ledger"].append({
                        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "agent": agent_conv,
                        "currency": "تحويل عملة",
                        "type": "مقاصة عملات",
                        "amount": 0,
                        "notes": f"تحويل ${amount_usd_to_convert:,.2f} إلى ({equivalent_iqd:,.0f} د.ع) بسعر {ex_rate:,.0f}",
                        "balance_after": f"${factory_data['agents'][agent_conv]['balance_usd']:,.2f} | {factory_data['agents'][agent_conv]['balance_iqd']:,.0f} د.ع",
                    })
                    save_all_factories(all_factories)
                    st.success("✅ تم إجراء التحويل بنجاح!")
                    st.rerun()
            else:
                if amount_iqd_to_convert <= 0:
                    st.error("لا يمكن إجراء تحويل بمبلغ 0!")
                else:
                    factory_data["agents"][agent_conv]["balance_iqd"] -= amount_iqd_to_convert
                    factory_data["agents"][agent_conv]["balance_usd"] += equivalent_usd

                    factory_data["agent_ledger"].append({
                        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "agent": agent_conv,
                        "currency": "تحويل عملة",
                        "type": "مقاصة عملات",
                        "amount": 0,
                        "notes": f"تحويل ({amount_iqd_to_convert:,.0f} د.ع) إلى (${equivalent_usd:,.2f}) بسعر {ex_rate:,.0f}",
                        "balance_after": f"${factory_data['agents'][agent_conv]['balance_usd']:,.2f} | {factory_data['agents'][agent_conv]['balance_iqd']:,.0f} د.ع",
                    })
                    save_all_factories(all_factories)
                    st.success("✅ تم إجراء التحويل بنجاح!")
                    st.rerun()
