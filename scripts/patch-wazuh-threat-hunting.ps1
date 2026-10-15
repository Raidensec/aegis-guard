[CmdletBinding()]
param(
    [string]$ContainerName = "wazuh-dashboard",
    [int]$HealthTimeoutSeconds = 240
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$routeSource = Join-Path $root "config\wazuh-dashboard\aegis-guard-route.js"
$pluginRoot = "/usr/share/wazuh-dashboard/plugins/wazuh"
$bundlePath = "$pluginRoot/target/public/wazuh.chunk.10.js"
$routesIndexPath = "$pluginRoot/server/routes/index.js"
$routeTargetPath = "$pluginRoot/server/routes/aegis-guard.js"
$marker = "AEGIS_GUARD_OLLAMA_ROW_ACTION"

if (-not (Test-Path $routeSource)) {
    throw "Aegis Guard route source not found: $routeSource"
}

$containerState = docker inspect --format '{{.State.Status}}' $ContainerName 2>$null
if ($LASTEXITCODE -ne 0 -or $containerState -ne "running") {
    throw "Container $ContainerName is not running"
}

$tempRoot = Join-Path $env:TEMP "aegis-wazuh-dashboard-patch"
New-Item -ItemType Directory -Path $tempRoot -Force | Out-Null
$bundleFile = Join-Path $tempRoot "wazuh.chunk.10.js"
$routesIndexFile = Join-Path $tempRoot "routes-index.js"

docker cp "${ContainerName}:$bundlePath" $bundleFile
if ($LASTEXITCODE -ne 0) { throw "Unable to copy the Wazuh Threat Hunting bundle" }

$bundle = [IO.File]::ReadAllText($bundleFile)
$helperMarker = "function events_extends(){"
$helper = @'
/* AEGIS_GUARD_OLLAMA_ROW_ACTION */
const AEGIS_GUARD_ACTION_CLASS="aegisGuardOllamaAction";
function showAegisGuardResult(result,isError){
  const oldToast=document.getElementById("aegis-guard-ollama-toast");
  if(oldToast){oldToast.remove()}
  const toast=document.createElement("div");
  toast.id="aegis-guard-ollama-toast";
  toast.setAttribute("role","status");
  toast.style.cssText="position:fixed;right:24px;top:76px;z-index:10000;width:min(420px,calc(100vw - 48px));padding:16px;border:1px solid "+(isError?"#BD271E":"#017D73")+";border-radius:6px;background:#1D1E24;color:#F5F7FA;box-shadow:0 8px 24px rgba(0,0,0,.35);font:14px/1.45 sans-serif";
  const title=document.createElement("strong");
  title.textContent=isError?"Ollama analysis failed":"Aegis Guard analysis complete";
  title.style.display="block";
  title.style.marginBottom="6px";
  const message=document.createElement("div");
  message.textContent=isError?(result.message||"Unable to analyze this event"):(result.ai_summary||"The event was analyzed and added to the Aegis Guard dashboard.");
  const actions=document.createElement("div");
  actions.style.cssText="display:flex;justify-content:flex-end;gap:12px;margin-top:12px";
  if(!isError){
    const link=document.createElement("a");
    link.href="/app/dashboards#/view/ai-soc-ollama-response";
    link.textContent="Open response dashboard";
    link.style.cssText="color:#36A2EF;font-weight:600";
    actions.appendChild(link)
  }
  const close=document.createElement("button");
  close.type="button";
  close.textContent="Close";
  close.style.cssText="border:0;background:transparent;color:#D3DAE6;cursor:pointer";
  close.onclick=()=>toast.remove();
  actions.appendChild(close);
  toast.appendChild(title);
  toast.appendChild(message);
  toast.appendChild(actions);
  document.body.appendChild(toast)
}
function addAegisGuardHeader(){
  const headerRow=document.querySelector(".kbn-table thead tr");
  if(!headerRow||headerRow.querySelector(".aegisGuardOllamaHeader")){return}
  const header=document.createElement("th");
  header.className="aegisGuardOllamaHeader";
  header.scope="col";
  header.textContent="Aegis Guard";
  header.style.cssText="min-width:152px;white-space:nowrap";
  headerRow.appendChild(header)
}
async function waitForAegisGuardJob(jobId){
  const deadline=Date.now()+360000;
  while(Date.now()<deadline){
    const response=await fetch("/api/aegis-guard/analyze/"+encodeURIComponent(jobId),{credentials:"same-origin",headers:{"osd-xsrf":"true"}});
    const job=await response.json();
    if(!response.ok){throw new Error(job.message||job.detail||"Unable to read analysis status")}
    if(job.status==="completed"){return job.result}
    if(job.status==="failed"){throw new Error(job.error||"Ollama analysis failed")}
    await new Promise(resolve=>setTimeout(resolve,2000))
  }
  throw new Error("Ollama analysis did not finish within six minutes")
}
function addAegisGuardAction(rowElement,rowData){
  if(!rowElement||!rowData||rowElement.querySelector("."+AEGIS_GUARD_ACTION_CLASS)){return}
  const cell=document.createElement("td");
  cell.className=AEGIS_GUARD_ACTION_CLASS;
  cell.style.cssText="min-width:152px;vertical-align:middle";
  const button=document.createElement("button");
  button.type="button";
  button.className="euiButton euiButton--primary euiButton--small";
  button.textContent="Analyze with Ollama";
  button.title="Send this event to Aegis Guard for Ollama analysis";
  button.setAttribute("aria-label",button.title);
  button.style.cssText="min-width:140px;min-height:30px;padding:4px 10px;border:1px solid #36A2EF;border-radius:4px;background:#005B96;color:#fff;font-weight:600;cursor:pointer;white-space:nowrap";
  button.onclick=async()=>{
    button.disabled=true;
    button.textContent="Analyzing...";
    button.style.cursor="wait";
    try{
      const alert=rowData._source||rowData;
      const response=await fetch("/api/aegis-guard/analyze",{method:"POST",credentials:"same-origin",headers:{"Content-Type":"application/json","osd-xsrf":"true"},body:JSON.stringify({alert:alert})});
      const queued=await response.json();
      if(!response.ok){throw new Error(queued.message||queued.detail||"Analysis request failed")}
      button.textContent="Ollama working...";
      const result=await waitForAegisGuardJob(queued.job_id);
      button.textContent="Analyzed";
      button.style.background="#017D73";
      button.style.borderColor="#54B399";
      button.style.cursor="default";
      showAegisGuardResult(result,false)
    }catch(error){
      button.disabled=false;
      button.textContent="Retry Ollama";
      button.style.background="#BD271E";
      button.style.borderColor="#E7664C";
      button.style.cursor="pointer";
      showAegisGuardResult({message:error.message},true)
    }
  };
  cell.appendChild(button);
  rowElement.appendChild(cell)
}
'@

$helperStart = $bundle.IndexOf("/* $marker */")
if ($helperStart -ge 0) {
    $eventsStart = $bundle.IndexOf($helperMarker, $helperStart)
    if ($eventsStart -lt 0) {
        throw "Wazuh bundle structure changed: Events helper marker not found"
    }
    $bundle = $bundle.Substring(0, $helperStart) + $helper + $bundle.Substring($eventsStart)
} else {
    if (-not $bundle.Contains($helperMarker)) {
        throw "Wazuh bundle structure changed: Events helper marker not found"
    }
    $bundle = $bundle.Replace($helperMarker, "$helper$helperMarker")
}

$currentRows = 'const discoverTableRows=document.querySelectorAll(".kbn-table tbody tr.kbnDocTable__row");discoverTableRows.forEach((row,rowIndex)=>{'
$patchedCurrentRows = 'const discoverTableRows=document.querySelectorAll(".kbn-table tbody tr.kbnDocTable__row");addAegisGuardHeader();discoverTableRows.forEach((row,rowIndex)=>{'
if ($bundle.Contains($currentRows)) {
    $bundle = $bundle.Replace($currentRows, $patchedCurrentRows)
} elseif (-not $bundle.Contains($patchedCurrentRows)) {
    throw "Wazuh bundle structure changed: current row renderer not found"
}

$currentRowAction = '});if(addObserverDetails){const rowDetails=row.nextElementSibling;'
$patchedCurrentRowAction = '});addAegisGuardAction(row,discoverRowsData[rowIndex]);if(addObserverDetails){const rowDetails=row.nextElementSibling;'
if ($bundle.Contains($currentRowAction)) {
    $bundle = $bundle.Replace($currentRowAction, $patchedCurrentRowAction)
} elseif (-not $bundle.Contains($patchedCurrentRowAction)) {
    throw "Wazuh bundle structure changed: current row action point not found"
}

$scrollingRows = 'enhanceDiscoverEventsCell(header.textContent,cell.textContent,discoverRowsData[rowIndex],cell,options)})}else{this.enhanceDiscoverTableRowDetailsAddObserver'
$patchedScrollingRows = 'enhanceDiscoverEventsCell(header.textContent,cell.textContent,discoverRowsData[rowIndex],cell,options)});addAegisGuardAction(mutationElement,discoverRowsData[rowIndex])}else{this.enhanceDiscoverTableRowDetailsAddObserver'
if ($bundle.Contains($scrollingRows)) {
    $bundle = $bundle.Replace($scrollingRows, $patchedScrollingRows)
} elseif (-not $bundle.Contains($patchedScrollingRows)) {
    throw "Wazuh bundle structure changed: scrolling row action point not found"
}

[IO.File]::WriteAllText($bundleFile, $bundle, (New-Object Text.UTF8Encoding($false)))
docker cp $bundleFile "${ContainerName}:$bundlePath"
if ($LASTEXITCODE -ne 0) { throw "Unable to install the patched Threat Hunting bundle" }

docker cp $routeSource "${ContainerName}:$routeTargetPath"
if ($LASTEXITCODE -ne 0) { throw "Unable to install the Aegis Guard dashboard route" }

docker cp "${ContainerName}:$routesIndexPath" $routesIndexFile
if ($LASTEXITCODE -ne 0) { throw "Unable to copy the Wazuh route registry" }
$routesIndex = [IO.File]::ReadAllText($routesIndexFile)
if (-not $routesIndex.Contains('require("./aegis-guard")')) {
    $requireMarker = 'var _wazuhReporting = require("./wazuh-reporting");'
    $routeMarker = '  (0, _wazuhUtils.UiLogsRoutes)(router);'
    if (-not $routesIndex.Contains($requireMarker) -or -not $routesIndex.Contains($routeMarker)) {
        throw "Wazuh route registry structure changed"
    }
    $routesIndex = $routesIndex.Replace(
        $requireMarker,
        "$requireMarker`r`n`r`nvar _aegisGuard = require(`"./aegis-guard`");"
    )
    $routesIndex = $routesIndex.Replace(
        $routeMarker,
        "$routeMarker`r`n  (0, _aegisGuard.AegisGuardRoutes)(router);"
    )
    [IO.File]::WriteAllText($routesIndexFile, $routesIndex, (New-Object Text.UTF8Encoding($false)))
    docker cp $routesIndexFile "${ContainerName}:$routesIndexPath"
    if ($LASTEXITCODE -ne 0) { throw "Unable to register the Aegis Guard dashboard route" }
}

# Remove stale pre-compressed copies so the dashboard serves the patched bundle.
docker exec $ContainerName sh -c "rm -f '$bundlePath.br' '$bundlePath.gz'"
if ($LASTEXITCODE -ne 0) { throw "Unable to remove stale compressed dashboard assets" }

docker restart $ContainerName | Out-Null
if ($LASTEXITCODE -ne 0) { throw "Unable to restart $ContainerName" }

$deadline = (Get-Date).AddSeconds($HealthTimeoutSeconds)
while ((Get-Date) -lt $deadline) {
    $health = docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' $ContainerName 2>$null
    if ($health -eq "healthy") {
        Write-Host "Aegis Guard Threat Hunting action installed."
        exit 0
    }
    Start-Sleep -Seconds 5
}

throw "$ContainerName did not become healthy within $HealthTimeoutSeconds seconds"
