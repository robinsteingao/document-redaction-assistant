from __future__ import annotations

import json
from pathlib import Path


def build_desktop_shell(output_root: Path | str, *, version: str, service_url: str | None = None) -> Path:
    root = Path(output_root) / f"desktop_shell_{version}"
    root.mkdir(parents=True, exist_ok=True)
    backend = "local_service" if service_url else "local_cli"
    (root / "app_config.json").write_text(
        json.dumps({
            "name": "文档安全脱敏助手",
            "version": version,
            "mode": "pilot_static_shell",
            "backend": backend,
            "service_url": service_url,
        }, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (root / "index.html").write_text(_html(version, service_url), encoding="utf-8")
    return root


def _html(version: str, service_url: str | None) -> str:
    service = service_url or ""
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>文档安全脱敏助手</title>
  <style>
    :root {{ --ink:#17212b; --muted:#536271; --line:#d7dee6; --accent:#0f766e; --bg:#edf2f5; }}
    body {{ margin:0; font-family:"Microsoft YaHei","Segoe UI",sans-serif; background:var(--bg); color:var(--ink); }}
    main {{ max-width:1040px; margin:0 auto; padding:32px; }}
    header {{ display:flex; justify-content:space-between; align-items:flex-end; margin-bottom:24px; }}
    h1 {{ margin:0; font-size:28px; }}
    .steps {{ display:grid; grid-template-columns:repeat(4,1fr); gap:14px; }}
    .step {{ background:white; border:1px solid var(--line); border-radius:8px; padding:18px; min-height:120px; }}
    .step b {{ display:block; font-size:18px; margin-bottom:10px; }}
    .note {{ background:#fff; border-left:4px solid var(--accent); padding:14px; margin-top:20px; }}
    .tool {{ background:white; border:1px solid var(--line); border-radius:8px; padding:18px; margin-top:20px; }}
    .grid {{ display:grid; grid-template-columns:1fr 1fr; gap:14px; }}
    .actions {{ display:flex; gap:10px; flex-wrap:wrap; margin-top:12px; }}
    label {{ display:block; font-weight:700; margin:10px 0 6px; }}
    input, textarea, select {{ width:100%; box-sizing:border-box; border:1px solid var(--line); border-radius:6px; padding:9px; font-family:inherit; font-size:14px; background:white; }}
    textarea {{ min-height:86px; resize:vertical; }}
    .hint {{ color:var(--muted); font-size:13px; margin:6px 0 0; }}
    .gate {{ background:#fff7ed; border:1px solid #fed7aa; border-radius:8px; padding:12px; margin-top:12px; color:#9a3412; }}
    pre {{ white-space:pre-wrap; word-break:break-word; background:#f7fafc; border:1px solid var(--line); border-radius:6px; padding:12px; min-height:48px; }}
    button {{ padding:9px 14px; border:0; border-radius:6px; background:var(--accent); color:white; cursor:pointer; }}
    button.secondary {{ background:#475569; }}
    button.danger {{ background:#b91c1c; }}
    code {{ background:white; padding:2px 5px; border-radius:4px; }}
  </style>
</head>
<body>
<main>
  <header>
    <div><h1>文档安全脱敏助手</h1><p>客户侧本地试点壳 v{version}</p></div>
    <div>原始文件不上传 | 映射表本地保存</div>
  </header>
  <section class="steps">
    <div class="step"><b>导入文件</b>选择 DOCX、XLSX、DOC、XLS、WPS、文本 PDF，或直接填写文件夹做批量处理。</div>
    <div class="step"><b>字段复核</b>检查项目、单位、金额、专利和技术指标。</div>
    <div class="step"><b>生成结果包</b>生成可交给 STPE-AI 沙箱导入的结果文件，并在本机保存映射表。</div>
    <div class="step"><b>报告还原</b>评审后使用本地映射表还原报告。</div>
  </section>
  <section class="note">
    <b>本地服务状态</b>
    <p id="serviceStatus">未检测</p>
    <button onclick="checkOcr()">检查 OCR</button>
    <p>本页面绑定本地服务接口：<code>{service or '未配置，使用 CLI 模式'}</code></p>
  </section>
  <section class="tool">
    <h2>生成脱敏结果包</h2>
    <div class="grid">
      <div>
        <label for="projectAlias">项目代号</label>
        <input id="projectAlias" value="INTERNAL-TEST-001">
      </div>
      <div>
        <label for="outputDir">输出目录</label>
        <input id="outputDir" value="desktop_output">
        <p class="hint">相对路径会自动保存到“文档\\文档安全脱敏助手输出”，避免安装目录无写入权限。</p>
      </div>
    </div>
    <div class="grid">
      <div>
        <label for="inputPaths">待处理文件或文件夹路径（支持批量）</label>
        <textarea id="inputPaths" placeholder="每行一个完整路径，可填写文件夹，例如 C:\\Users\\tester\\Desktop\\项目材料"></textarea>
      </div>
      <div>
        <label for="ocrMode">PDF OCR 模式</label>
        <select id="ocrMode">
          <option value="quick" selected>快速预览：每个 PDF 先识别 1 页</option>
          <option value="full">完整处理：按本地默认页数识别</option>
        </select>
        <p class="hint">旧版 DOC/XLS/WPS 会先尝试本地转换；转换失败的文件不会静默上传。</p>
      </div>
    </div>
    <div class="actions">
      <button onclick="runInputPlan()">预检文件</button>
      <button onclick="startBuildJob()">开始生成脱敏结果包</button>
      <button class="danger" onclick="cancelCurrentJob()">取消当前任务</button>
      <button class="secondary" onclick="retryCurrentJob()">重试失败任务</button>
    </div>
    <div class="gate">
      <b>评价影响提醒（生成前必看）</b>
      <p>如需改默认处理方式，请先生成一次结果包，打开输出目录中的 <code>review_workspace.html</code>，导出 <code>review_decisions.json</code>，用记事本打开后按提示修改，再粘贴回下方重跑。技术指标、验证信息、金额、专利等关键字段如果被强制隐藏，可能影响后续评价。</p>
      <label for="reviewDecisions">自定义字段处理方式（可选）</label>
      <textarea id="reviewDecisions" placeholder='可粘贴 review_decisions.json 内容。简单理解：action=keep 表示保留原样；action=redact 表示隐藏；strategy 可选 pseudonym(假名)、mask(遮盖)、range(区间)。'></textarea>
      <label style="display:flex;align-items:center;gap:8px;font-weight:400;margin-top:10px;">
        <input id="confirmDegradationRisk" type="checkbox" style="width:auto;">
        我已确认：如强制脱敏高影响评价字段，可能导致 STPE-AI 评价降级，并接受该风险。
      </label>
    </div>
    <h3>预检结果摘要</h3>
    <pre id="planResult">等待预检</pre>
    <h3>处理进度摘要</h3>
    <pre id="buildResult">等待操作</pre>
  </section>
</main>
<script>
const serviceUrl = {json.dumps(service, ensure_ascii=False)};
let currentJobId = null;
function localServiceHelp(err) {{
  return '本地服务未连接。请先运行 app\\\\start_offline_app.bat 或 app\\\\start_local_service.bat，确认服务地址为 ' + serviceUrl + '，然后重试。浏览器错误：' + err.message + '。常见原始提示包括 Failed to fetch。';
}}
async function checkOcr() {{
  const el = document.getElementById('serviceStatus');
  if (!serviceUrl) {{
    el.textContent = '当前未配置本地服务，请使用命令行模式。';
    return;
  }}
  try {{
    const res = await fetch(serviceUrl + '/ocr-status');
    const body = await res.json();
    el.textContent = JSON.stringify(body, null, 2) + '\\n\\n完成后请打开 outputs.output_dir 对应的文件夹。';
  }} catch (err) {{
    el.textContent = localServiceHelp(err);
  }}
}}
async function postJson(path, payload) {{
  const res = await fetch(serviceUrl + path, {{
    method: 'POST',
    headers: {{'Content-Type':'application/json'}},
    body: JSON.stringify(payload)
  }});
  return await res.json();
}}
function readPayload() {{
  const input_paths = document.getElementById('inputPaths').value.split(/\\r?\\n/).map(v => v.trim()).filter(Boolean);
  const out = document.getElementById('outputDir').value.trim();
  const project_alias_id = document.getElementById('projectAlias').value.trim();
  const ocr_mode = document.getElementById('ocrMode').value;
  const rawDecisions = document.getElementById('reviewDecisions').value.trim();
  const confirmedRisk = document.getElementById('confirmDegradationRisk').checked === true;
  const payload = {{project_alias_id, out, input_paths, ocr_mode, enable_conversion: true}};
  if (rawDecisions) {{
    try {{ payload.review_decisions = JSON.parse(rawDecisions); }}
    catch (err) {{ throw new Error('自定义字段处理方式 JSON 格式错误：' + err.message); }}
  }}
  if (confirmedRisk) payload.customer_confirmed_degradation_risk = true;
  return payload;
}}
function rawDetails(body) {{
  return '\\n\\n原始详情（供技术支持复制，可不用逐行理解）：\\n' + JSON.stringify(body, null, 2);
}}
function listCount(items) {{
  return Array.isArray(items) ? items.length : 0;
}}
function formatPlanResult(body) {{
  if (!body || body.success === false) {{
    return '预检失败：' + ((body && body.error) || '未知错误') + rawDetails(body || {{}});
  }}
  const r = body.result || {{}};
  const modes = Array.isArray(r.recommended_ocr_modes) ? r.recommended_ocr_modes.join('、') : '按默认设置';
  const lines = [
    '预检完成，请重点看下面几项：',
    '可直接处理文件数：' + (r.processable_count || 0),
    '需先转换文件数：' + (r.convertible_count || 0),
    '跳过文件数：' + (r.skipped_count || 0),
    '暂不支持文件数：' + (r.unsupported_count || 0),
    '推荐 OCR 模式：' + modes
  ];
  if (listCount(r.convertible_files)) lines.push('提示：发现旧版 Office/WPS 文件，系统会先尝试本地转换。');
  if (listCount(r.skipped_files)) lines.push('提示：有文件被跳过，请在原始详情中查看文件名和原因。');
  return lines.join('\\n') + rawDetails(body);
}}
function formatJobStatus(body) {{
  if (!body || body.success === false) {{
    return '任务失败：' + ((body && body.error) || '未知错误') + rawDetails(body || {{}});
  }}
  const r = body.result || {{}};
  const progress = r.progress || {{}};
  const outputs = r.outputs || {{}};
  const lines = [
    '任务状态：' + (r.status || '未知'),
    '任务编号：' + (r.job_id || currentJobId || '未返回'),
    '处理进度：' + (progress.current || 0) + '/' + (progress.total || 0),
    '当前文件：' + (progress.file_name || '暂无'),
    '输出目录：' + (outputs.output_dir || r.output_dir || '完成后显示'),
    '错误提示：' + (r.error || '无')
  ];
  if (outputs.package) lines.push('结果包文件：' + outputs.package);
  if (outputs.sandbox_import_package) lines.push('沙箱导入文件：' + outputs.sandbox_import_package);
  return lines.join('\\n') + rawDetails(body);
}}
async function runInputPlan() {{
  const el = document.getElementById('planResult');
  let payload;
  try {{ payload = readPayload(); }} catch (err) {{ el.textContent = err.message; return; }}
  if (!serviceUrl) {{
    el.textContent = '当前未配置本地服务，请使用命令行模式。';
    return;
  }}
  if (payload.input_paths.length === 0) {{
    el.textContent = '请至少输入一个文件或文件夹路径。';
    return;
  }}
  el.textContent = '正在预检文件...';
  try {{
    const body = await postJson('/plan-inputs', payload);
    el.textContent = formatPlanResult(body);
  }} catch (err) {{
    el.textContent = localServiceHelp(err);
  }}
}}
async function startBuildJob() {{
  const el = document.getElementById('buildResult');
  let payload;
  try {{ payload = readPayload(); }} catch (err) {{ el.textContent = err.message; return; }}
  if (!serviceUrl) {{
    el.textContent = '当前未配置本地服务，请使用命令行模式。';
    return;
  }}
  if (!payload.project_alias_id || !payload.out || payload.input_paths.length === 0) {{
    el.textContent = '请填写项目代号、输出目录，并至少输入一个文件或文件夹路径。';
    return;
  }}
  el.textContent = '正在创建后台任务...';
  try {{
    const body = await postJson('/start-build', payload);
    el.textContent = formatJobStatus(body);
    if (body.success && body.result && body.result.job_id) {{
      currentJobId = body.result.job_id;
      pollJob(body.result.job_id);
    }}
  }} catch (err) {{
    el.textContent = localServiceHelp(err);
  }}
}}
async function pollJob(jobId) {{
  const el = document.getElementById('buildResult');
  for (;;) {{
    const res = await fetch(serviceUrl + '/job-status?job_id=' + encodeURIComponent(jobId));
    const body = await res.json();
    el.textContent = formatJobStatus(body);
    const status = body.result && body.result.status;
    if (status === 'completed' || status === 'failed' || status === 'cancelled') {{
      return;
    }}
    await new Promise(resolve => setTimeout(resolve, 1000));
  }}
}}
async function runBuildPackage() {{
  return startBuildJob();
}}
async function cancelCurrentJob() {{
  const el = document.getElementById('buildResult');
  if (!currentJobId) {{
    el.textContent = '当前没有正在跟踪的任务。';
    return;
  }}
  try {{
    const body = await postJson('/cancel-job', {{job_id: currentJobId}});
    el.textContent = formatJobStatus(body);
  }} catch (err) {{
    el.textContent = localServiceHelp(err);
  }}
}}
async function retryCurrentJob() {{
  const el = document.getElementById('buildResult');
  if (!currentJobId) {{
    el.textContent = '当前没有可重试的任务。';
    return;
  }}
  try {{
    const body = await postJson('/retry-job', {{job_id: currentJobId}});
    el.textContent = formatJobStatus(body);
    if (body.success && body.result && body.result.job_id) {{
      currentJobId = body.result.job_id;
      pollJob(currentJobId);
    }}
  }} catch (err) {{
    el.textContent = localServiceHelp(err);
  }}
}}
</script>
</body>
</html>"""
