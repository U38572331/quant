
import sys
import os
import streamlit.web.cli as stcli

def main():
    # When frozen, the dashboard.py will be in the internal _MEI folder
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
        
    dashboard_path = os.path.join(base_path, "dashboard.py")
    
    # Set arguments for streamlit run
    # we simulate "streamlit run dashboard.py --global.developmentMode=false"
    sys.argv = [
        "streamlit",
        "run",
        dashboard_path,
        "--global.developmentMode=false",
    ]
    
    print(f"Launching dashboard from {dashboard_path}")
    sys.exit(stcli.main())

if __name__ == "__main__":
    # Standard boilerplate for multiprocessing support on Windows
    # (Though streamlit might not strictly need it, openbb extensions might)
    from multiprocessing import freeze_support
    freeze_support()
    main()
