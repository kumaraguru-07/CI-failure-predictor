"""Local Failure-Aware CI dashboard. Run with streamlit run app.py."""
import hashlib
import json
from pathlib import Path
import pandas as pd
import streamlit as st
from src.dashboard_data import (PROJECT_ROOT,fingerprint,DashboardService,validation_data,
    parse_feature_csv,csv_download,add_history)
from src.explain import report_markdown

st.set_page_config(page_title="Failure-aware CI",page_icon=":material/monitoring:",layout="wide")
ROOT = PROJECT_ROOT
st.session_state.setdefault("prediction_history",[])
st.session_state.setdefault("last_explanation",None)

st.title("Failure-aware CI")
st.caption("Explore build risk, understand the model signals, and plan your CI checks.")
with st.sidebar:
    st.subheader("Workspace")
    view = st.selectbox("View",["Explore builds","Predict from CSV","Model results","Session history"],key="view")
    st.info("Local research dashboard · historical data")
    st.caption("Live GitHub extraction is the next project stage.")
    st.caption("All mandatory CI checks remain required.")

@st.cache_resource(max_entries=2,show_spinner="Loading the verified prediction model…")
def get_service(root,signature):
    return DashboardService(root)

@st.cache_data(max_entries=2,show_spinner="Loading historical builds…")
def get_validation(root,signature,_service):
    return validation_data(root,_service)

try:
    signature = fingerprint(ROOT)
    service = get_service(str(ROOT),signature)
    features,builds = get_validation(str(ROOT),signature,service)
except (FileNotFoundError,ValueError,KeyError,OSError) as exc:
    st.error("The dashboard could not load its verified local model or dataset.")
    st.caption(str(exc))
    st.info("Check docs/DASHBOARD.md for the required files and recovery commands.")
    st.stop()

st.caption("Model: enhanced Random Forest · score bands selected on validation data")
st.warning("Research baseline: many warnings are false alarms. A low score does not guarantee a successful build.")

def show_prediction(frame,input_id,source,actual="Unknown"):
    if st.button("Analyze this build",type="primary",key="analyze"):
        try:
            with st.spinner("Computing prediction and explanation…"):
                result = service.explain(frame)
            st.session_state.last_explanation = {"input_id":input_id,"result":result}
            st.session_state.prediction_history = add_history(st.session_state.prediction_history,result,source,actual)
        except (ValueError,AssertionError,TypeError) as exc:
            st.session_state.last_explanation = None
            st.error("This input could not be explained. Check its feature values.")
            st.caption(str(exc))
    saved = st.session_state.last_explanation
    if saved is None or saved["input_id"]!=input_id:
        st.info("Choose a build and select Analyze this build to see its explanation.")
        return
    result = saved["result"]
    with st.container(horizontal=True):
        st.metric("Estimated failure probability",f"{result['failure_probability']:.1%}",border=True)
        st.metric("Risk band",result["risk_level"],border=True)
        st.metric("Recorded outcome",actual,border=True)
    if result["missing_input_features"]:
        st.warning(result["input_quality_note"])
    else:
        st.caption(result["input_quality_note"])
    left,right = st.columns([3,2])
    with left:
        st.subheader("What influenced this score")
        factors = result["top_increasing_signals"]+result["top_decreasing_signals"]
        chart = pd.DataFrame([{"Signal":f["feature"].replace("_"," "),
            "Effect (percentage points)":f["contribution_percentage_points"],
            "Color":"#d15c48" if f["contribution"]>0 else "#21877a"} for f in factors])
        if len(chart):
            st.bar_chart(chart,x="Signal",y="Effect (percentage points)",color="Color",horizontal=True,height=310)
        else:
            st.info("No individual signal changed the background score.")
        st.caption("Positive values raise the score; negative values lower it. These are model associations, not proven failure causes.")
    with right:
        with st.container(border=True):
            st.subheader("Recommended CI order")
            for action in result["ci_recommendation"]["priority"]:
                st.write("• "+action)
            st.success("Run all mandatory checks before merging.")
            st.caption("Advice only: the dashboard does not schedule or skip tests.")
    with st.expander("Full explanation and input values"):
        table = pd.DataFrame(result["all_contributions"])[["feature","input_value","value_used","input_was_missing","contribution_percentage_points"]]
        table.columns = ["Signal","Supplied value","Model value","Input missing","Effect (percentage points)"]
        st.dataframe(table,hide_index=True)
        st.caption(f"Background score: {result['base_probability']:.2%} · Reconstruction error: {result['additivity_error']:.3g}")
        st.caption("Attribution method: "+result["attribution_method"])
    report = {"risk_thresholds":service.engine.bundle["thresholds"],"rows":[result]}
    with st.container(horizontal=True):
        st.download_button("Download explanation JSON",json.dumps(report,indent=2,allow_nan=False),file_name="build_explanation.json",mime="application/json")
        st.download_button("Download readable report",report_markdown(report),file_name="build_explanation.md",mime="text/markdown")

if view=="Explore builds":
    st.subheader("Explore historical builds")
    st.caption("Recorded validation builds with known outcomes. Outcomes are shown for comparison and are never prediction inputs. Times are UTC.")
    repository = st.selectbox("Repository",["All repositories"]+sorted(builds.repository.unique().tolist()),key="repository")
    risk = st.selectbox("Risk band",["All risk levels","LOW","MEDIUM","HIGH"],key="risk_filter")
    filtered = builds
    if repository!="All repositories":
        filtered = filtered[filtered.repository.eq(repository)]
    if risk!="All risk levels":
        filtered = filtered[filtered.risk_level.eq(risk)]
    with st.container(horizontal=True):
        st.metric("Builds in view",f"{len(filtered):,}",border=True)
        st.metric("High-risk builds",f"{filtered.risk_level.eq('HIGH').sum():,}",border=True)
        st.metric("Recorded failures",f"{filtered.actual_outcome.eq('Failed').sum():,}",border=True)
    if filtered.empty:
        st.info("No builds match these filters. Choose a different repository or risk band.")
    else:
        shown = filtered.sort_values("started_at",ascending=False).head(200)
        display = shown[["repository","started_at","risk_level","failure_probability","actual_outcome"]].copy()
        display.columns = ["Repository","Build time (UTC)","Risk","Failure probability","Actual outcome"]
        st.dataframe(display,hide_index=True,column_config={"Failure probability":st.column_config.NumberColumn(format="percent")},height=270)
        st.caption(f"Showing the newest {len(shown)} matching builds.")
        position = st.selectbox("Build to inspect",shown.row_position.tolist(),
            format_func=lambda n:f"{builds.iloc[n].repository} · {builds.iloc[n].started_at:%Y-%m-%d %H:%M} UTC · {str(builds.iloc[n].commit_sha)[:8]} · row {n}",
            key="build_position")
        row = builds.iloc[int(position)]
        show_prediction(features.iloc[[int(position)]],f"validation:{signature}:{position}",
            f"Historical row {position}",row.actual_outcome)
        st.download_button("Download filtered predictions",csv_download(filtered.drop(columns=["row_position"])),
            file_name="historical_predictions.csv",mime="text/csv")

elif view=="Predict from CSV":
    st.subheader("Predict from a feature CSV")
    st.write("Supply pre-build features using the template. Empty numeric cells use training medians. Maximum 500 rows and 5 MB.")
    st.download_button("Download feature CSV template",csv_download(features[service.engine.bundle["features"]].head(3)),
        file_name="feature_template.csv",mime="text/csv")
    uploaded = st.file_uploader("Feature CSV",type=["csv"],key="feature_csv")
    if uploaded is None:
        st.info("Download the template, replace its values, then upload it here.")
    else:
        try:
            content = uploaded.getvalue()
            data,ignored = parse_feature_csv(content,service.engine.bundle["features"])
            if ignored:
                st.info("Excluded extra columns: "+", ".join(ignored))
            predictions = service.predict(data)
            table = predictions.copy()
            table.insert(0,"Input row",range(1,len(table)+1))
            st.dataframe(table,hide_index=True,column_config={"failure_probability":st.column_config.NumberColumn("Failure probability",format="percent")})
            number = st.number_input("Input row to explain",min_value=1,max_value=len(data),value=1,step=1,key="upload_row")
            index = int(number)-1
            if not 0<=index<len(data):
                raise ValueError("Select an input row within the uploaded file")
            show_prediction(data.iloc[[index]],f"upload:{service.manifest['model_sha256']}:{hashlib.sha256(content).hexdigest()}:{index}",
                f"Uploaded feature row {index+1}")
            st.download_button("Download batch predictions",csv_download(table),file_name="batch_predictions.csv",mime="text/csv")
        except (ValueError,TypeError) as exc:
            st.error(str(exc))

elif view=="Model results":
    st.subheader("Frozen model evaluation")
    report = service.manifest
    st.caption("Saved evaluation only. Opening this page does not train a model or re-evaluate the test set.")
    result = report["test"]
    with st.container(horizontal=True):
        st.metric("Failure detection (recall)",f"{result['recall']:.1%}",border=True)
        st.metric("Warning precision",f"{result['precision']:.1%}",border=True)
        st.metric("Average precision",f"{result['average_precision']:.3f}",border=True)
        st.metric("Test builds",f"{result['rows']:,}",border=True)
    st.subheader("Validation comparison")
    comparison = pd.DataFrame([{"Candidate":name.replace("_"," "),"Average precision":v["average_precision"]}
        for name,v in report["validation_comparison"].items()])
    st.bar_chart(comparison,x="Candidate",y="Average precision",horizontal=True,height=270)
    tn,fp,fn,tp = result["confusion_matrix_tn_fp_fn_tp"]
    st.subheader("Test outcomes at the frozen warning threshold")
    st.table(pd.DataFrame([[tn,fp],[fn,tp]],index=["Actually passed","Actually failed"],columns=["No warning","Warning"]))
    cuts = report["thresholds"]
    st.write(f"LOW below {cuts['low_upper']:.2%}; MEDIUM below {cuts['medium_upper']:.2%}; HIGH at or above {cuts['medium_upper']:.2%}.")
    with st.expander("Dataset coverage and limitations"):
        audit = json.loads((ROOT/"reports/dataset_audit.json").read_text(encoding="utf-8"))
        st.write(f"{audit['raw_rows']:,} source records; {audit['eligible_rows']:,} eligible builds.")
        for item in report["limitations"]:
            st.write("• "+item)
        st.caption("File-level and configuration-change features are unavailable in the training source.")
    st.download_button("Download model evaluation",json.dumps(report,indent=2),file_name="model_evaluation.json",mime="application/json")

elif view=="Session history":
    st.subheader("Your prediction session")
    st.caption("Only builds you analyze are listed. This history is kept in this browser session (latest 100); download it before closing.")
    history = st.session_state.prediction_history
    if not history:
        st.info("Analyze a historical or uploaded build to start your session history.")
    else:
        st.dataframe(pd.DataFrame(history),hide_index=True,
            column_config={"failure_probability":st.column_config.NumberColumn("Failure probability",format="percent")})
        st.download_button("Download session history",csv_download(pd.DataFrame(history)),file_name="prediction_history.csv",mime="text/csv")
        if st.button("Clear session history",key="clear_history"):
            st.session_state.prediction_history = []
            st.session_state.last_explanation = None
            st.rerun()
