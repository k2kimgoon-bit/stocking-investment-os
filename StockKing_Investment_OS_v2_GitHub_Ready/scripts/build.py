from __future__ import annotations
import json, pathlib
from common import ROOT, DATA, now_kst, write_json

def write_dashboard(data):
    write_json(DATA/'dashboard.json',data)
    (DATA/'data.js').write_text('window.DASHBOARD_DATA = '+json.dumps(data,ensure_ascii=False,separators=(',',':'))+';\n',encoding='utf-8')
