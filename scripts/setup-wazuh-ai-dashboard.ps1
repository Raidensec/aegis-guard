[CmdletBinding()]
param(
    [string]$DashboardUrl = "https://localhost:443",
    [string]$Username = "admin",
    [string]$Password = "admin"
)

$ErrorActionPreference = "Stop"
[System.Net.ServicePointManager]::ServerCertificateValidationCallback = { $true }

$basicAuth = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes("$Username`:$Password"))
$headers = @{ "osd-xsrf" = "true"; Authorization = "Basic $basicAuth" }
$indexPatternId = "ai-soc-events"

function Save-SavedObject {
    param(
        [Parameter(Mandatory = $true)][string]$Type,
        [Parameter(Mandatory = $true)][string]$Id,
        [Parameter(Mandatory = $true)][hashtable]$Attributes,
        [array]$References = @()
    )

    $body = @{
        attributes = $Attributes
        references = $References
    } | ConvertTo-Json -Depth 50 -Compress

    $uri = "$DashboardUrl/api/saved_objects/$Type/$Id`?overwrite=true"
    Invoke-RestMethod -Uri $uri -Method Post -Headers $headers `
        -ContentType "application/json" -Body $body | Out-Null
    Write-Host "Saved $Type/$Id"
}

function New-SearchSource {
    param([string]$Query = "")

    return @{
        indexRefName = "kibanaSavedObjectMeta.searchSourceJSON.index"
        query = @{ query = $Query; language = "kuery" }
        filter = @()
    } | ConvertTo-Json -Depth 20 -Compress
}

function Save-Visualization {
    param(
        [string]$Id,
        [string]$Title,
        [string]$Description,
        [hashtable]$VisState,
        [string]$Query = "",
        [hashtable]$UiState = @{}
    )

    $VisState.title = $Title
    Save-SavedObject -Type "visualization" -Id $Id -Attributes @{
        title = $Title
        description = $Description
        version = 1
        visState = ($VisState | ConvertTo-Json -Depth 50 -Compress)
        uiStateJSON = ($UiState | ConvertTo-Json -Depth 20 -Compress)
        kibanaSavedObjectMeta = @{ searchSourceJSON = (New-SearchSource -Query $Query) }
    } -References @(
        @{ name = "kibanaSavedObjectMeta.searchSourceJSON.index"; id = $indexPatternId; type = "index-pattern" }
    )
}

function Save-Metric {
    param(
        [string]$Id,
        [string]$Title,
        [string]$Query,
        [string]$Aggregation = "count",
        [string]$Field = ""
    )

    $params = @{ customLabel = $Title }
    if ($Field) { $params.field = $Field }

    Save-Visualization -Id $Id -Title $Title -Description "AI SOC dashboard metric" -Query $Query -VisState @{
        type = "metric"
        aggs = @(
            @{ id = "1"; enabled = $true; type = $Aggregation; schema = "metric"; params = $params }
        )
        params = @{
            addTooltip = $true
            addLegend = $false
            type = "metric"
            metric = @{
                percentageMode = $false
                useRanges = $false
                colorSchema = "Green to Red"
                metricColorMode = "None"
                colorsRange = @(@{ from = 0; to = 10000 })
                labels = @{ show = $true }
                invertColors = $false
                style = @{ bgFill = "#000"; bgColor = $false; labelColor = $false; subText = ""; fontSize = 42 }
            }
        }
    }
}

function Save-Donut {
    param(
        [string]$Id,
        [string]$Title,
        [string]$Query,
        [string]$Field,
        [hashtable]$Colors
    )

    Save-Visualization -Id $Id -Title $Title -Description "AI SOC categorical breakdown" -Query $Query -UiState @{ vis = @{ colors = $Colors } } -VisState @{
        type = "pie"
        aggs = @(
            @{ id = "1"; enabled = $true; type = "count"; schema = "metric"; params = @{} },
            @{ id = "2"; enabled = $true; type = "terms"; schema = "segment"; params = @{
                field = $Field; order = "desc"; orderBy = "1"; size = 8; otherBucket = $false; missingBucket = $false
            }}
        )
        params = @{
            type = "pie"
            addTooltip = $true
            addLegend = $true
            legendPosition = "right"
            isDonut = $true
            labels = @{ show = $true; values = $true; last_level = $true; truncate = 24 }
        }
    }
}

Save-Visualization -Id "ai-soc-command-header" -Title "Aegis Guard" -Description "Dashboard identity and operating mode" -VisState @{
    type = "markdown"
    aggs = @()
    params = @{
        fontSize = 13
        openLinksInNewTab = $false
        markdown = "# AEGIS GUARD`n**WAZUH EVENTS** | **OLLAMA TRIAGE** | **MITRE / D3FEND RESPONSE** | **DRY RUN: ON**"
    }
}

Save-Metric -Id "ai-soc-kpi-triage" -Title "Events Analyzed" -Query 'event.dataset : "ai-soc.analysis"'
Save-Metric -Id "ai-soc-kpi-incidents" -Title "Unique Incidents" -Query 'ai_soc.incident.id : *' -Aggregation "cardinality" -Field "ai_soc.incident.id.keyword"
Save-Metric -Id "ai-soc-kpi-plans" -Title "Response Plans" -Query 'event.dataset : "ai-soc.response"'
Save-Metric -Id "ai-soc-kpi-pending" -Title "Pending Actions" -Query 'event.dataset : "ai-soc.response_action" and ai_soc.response.action.status : "pending"'

Save-Visualization -Id "ai-soc-event-timeline" -Title "AI Event Activity" -Description "Triage, plan, and response activity over time" -VisState @{
    type = "line"
    aggs = @(
        @{ id = "1"; enabled = $true; type = "count"; schema = "metric"; params = @{ customLabel = "Events" } },
        @{ id = "2"; enabled = $true; type = "date_histogram"; schema = "segment"; params = @{
            field = "@timestamp"; interval = "auto"; customInterval = "2h"; min_doc_count = 1; extended_bounds = @{}; drop_partials = $false
        }},
        @{ id = "3"; enabled = $true; type = "terms"; schema = "group"; params = @{
            field = "event.dataset.keyword"; order = "desc"; orderBy = "1"; size = 6; otherBucket = $false; missingBucket = $false
        }}
    )
    params = @{
        type = "line"
        addTooltip = $true
        addLegend = $true
        legendPosition = "right"
        smoothLines = $false
        grid = @{ categoryLines = $false; style = @{ color = "#eee" } }
        categoryAxes = @(@{
            id = "CategoryAxis-1"; type = "category"; position = "bottom"; show = $true
            style = @{}; scale = @{ type = "linear" }; labels = @{ show = $true; rotate = 0; truncate = 100 }; title = @{}
        })
        valueAxes = @(@{
            id = "ValueAxis-1"; name = "LeftAxis-1"; type = "value"; position = "left"; show = $true
            style = @{}; scale = @{ type = "linear"; mode = "normal"; setDomain = $false; defaultYExtents = $false }
            labels = @{ show = $true; rotate = 0; filter = $false; truncate = 100 }; title = @{ text = "Events" }
        })
        seriesParams = @(@{
            show = "true"; type = "line"; mode = "normal"; data = @{ label = "Events"; id = "1" }
            valueAxis = "ValueAxis-1"; drawLinesBetweenPoints = $true; showCircles = $true
        })
        times = @()
        addTimeMarker = $false
    }
} -Query 'event.module : "ai-soc"'

Save-Donut -Id "ai-soc-severity-donut" -Title "Alert Severity" -Query 'event.dataset : "ai-soc.analysis"' `
    -Field "ai_soc.severity.keyword" -Colors @{ critical = "#BD271E"; high = "#E7664C"; medium = "#F5A700"; low = "#54B399" }

Save-Donut -Id "ai-soc-approval-donut" -Title "Approval Decisions" -Query 'event.dataset : "ai-soc.response_action"' `
    -Field "ai_soc.response.action.approval_tier.keyword" -Colors @{ AUTO_SAFE = "#54B399"; RECOMMEND = "#6092C0"; HUMAN_REQUIRED = "#F5A700" }

Save-Visualization -Id "ai-soc-action-types" -Title "Planned Defense Actions" -Description "Response actions selected by the orchestrator" -Query 'event.dataset : "ai-soc.response_action"' -VisState @{
    type = "horizontal_bar"
    aggs = @(
        @{ id = "1"; enabled = $true; type = "count"; schema = "metric"; params = @{ customLabel = "Actions" } },
        @{ id = "2"; enabled = $true; type = "terms"; schema = "segment"; params = @{
            field = "ai_soc.response.action.action_type.keyword"; order = "desc"; orderBy = "1"; size = 10; otherBucket = $false; missingBucket = $false
        }}
    )
    params = @{
        type = "histogram"
        addTooltip = $true
        addLegend = $false
        legendPosition = "right"
        grid = @{ categoryLines = $false; style = @{ color = "#eee" } }
        categoryAxes = @(@{
            id = "CategoryAxis-1"; type = "category"; position = "left"; show = $true
            style = @{}; scale = @{ type = "linear" }; labels = @{ show = $true; rotate = 0; truncate = 100 }; title = @{}
        })
        valueAxes = @(@{
            id = "ValueAxis-1"; name = "BottomAxis-1"; type = "value"; position = "bottom"; show = $true
            style = @{}; scale = @{ type = "linear"; mode = "normal"; setDomain = $false; defaultYExtents = $false }
            labels = @{ show = $true; rotate = 0; filter = $false; truncate = 100 }; title = @{ text = "Actions" }
        })
        seriesParams = @(@{
            show = "true"; type = "histogram"; mode = "stacked"; data = @{ label = "Actions"; id = "1" }
            valueAxis = "ValueAxis-1"
        })
        times = @()
        addTimeMarker = $false
    }
}

Save-SavedObject -Type "search" -Id "ai-soc-incident-feed" -Attributes @{
    title = "AI SOC Incident Feed"
    description = "Compact Wazuh event and AI analysis feed"
    sort = @("@timestamp", "desc")
    columns = @(
        "@timestamp", "event.action", "ai_soc.severity", "wazuh.rule.level", "wazuh.rule.description",
        "source.ip", "destination.ip", "ai_soc.incident.id", "ai_soc.confidence", "ai_soc.summary"
    )
    kibanaSavedObjectMeta = @{ searchSourceJSON = (New-SearchSource -Query 'event.dataset : "ai-soc.analysis"') }
} -References @(
    @{ name = "kibanaSavedObjectMeta.searchSourceJSON.index"; id = $indexPatternId; type = "index-pattern" }
)

Save-SavedObject -Type "search" -Id "ai-soc-response-actions" -Attributes @{
    title = "Response Action Queue"
    description = "One row per action planned or executed by the response orchestrator"
    sort = @("@timestamp", "desc")
    columns = @(
        "@timestamp", "ai_soc.response.action.action_type", "ai_soc.response.action.target",
        "ai_soc.response.action.status", "ai_soc.response.action.approval_tier",
        "ai_soc.response.action.safety_score", "ai_soc.response.action.d3fend_label",
        "ai_soc.response.plan_id", "ai_soc.response.action.rationale"
    )
    kibanaSavedObjectMeta = @{ searchSourceJSON = (New-SearchSource -Query 'event.dataset : "ai-soc.response_action"') }
} -References @(
    @{ name = "kibanaSavedObjectMeta.searchSourceJSON.index"; id = $indexPatternId; type = "index-pattern" }
)

Save-SavedObject -Type "search" -Id "ai-soc-response-plans" -Attributes @{
    title = "Ollama Response Plans"
    description = "Generated defense plans and Ollama rationale"
    sort = @("@timestamp", "desc")
    columns = @(
        "@timestamp", "ai_soc.response.plan_id", "ai_soc.incident.id", "ai_soc.response.status",
        "ai_soc.response.ollama_model", "ai_soc.response.total_actions", "ai_soc.response.pending_approval_count",
        "ai_soc.response.pre_defense_risk", "ai_soc.response.ollama_response"
    )
    kibanaSavedObjectMeta = @{ searchSourceJSON = (New-SearchSource -Query 'event.dataset : "ai-soc.response"') }
} -References @(
    @{ name = "kibanaSavedObjectMeta.searchSourceJSON.index"; id = $indexPatternId; type = "index-pattern" }
)

$panels = @(
    @{ version = "2.10.0"; gridData = @{ x = 0; y = 0; w = 48; h = 4; i = "1" }; panelIndex = "1"; type = "visualization"; panelRefName = "panel_1"; embeddableConfig = @{} },
    @{ version = "2.10.0"; gridData = @{ x = 0; y = 4; w = 12; h = 7; i = "2" }; panelIndex = "2"; type = "visualization"; panelRefName = "panel_2"; embeddableConfig = @{} },
    @{ version = "2.10.0"; gridData = @{ x = 12; y = 4; w = 12; h = 7; i = "3" }; panelIndex = "3"; type = "visualization"; panelRefName = "panel_3"; embeddableConfig = @{} },
    @{ version = "2.10.0"; gridData = @{ x = 24; y = 4; w = 12; h = 7; i = "4" }; panelIndex = "4"; type = "visualization"; panelRefName = "panel_4"; embeddableConfig = @{} },
    @{ version = "2.10.0"; gridData = @{ x = 36; y = 4; w = 12; h = 7; i = "5" }; panelIndex = "5"; type = "visualization"; panelRefName = "panel_5"; embeddableConfig = @{} },
    @{ version = "2.10.0"; gridData = @{ x = 0; y = 11; w = 30; h = 13; i = "6" }; panelIndex = "6"; type = "visualization"; panelRefName = "panel_6"; embeddableConfig = @{} },
    @{ version = "2.10.0"; gridData = @{ x = 30; y = 11; w = 18; h = 13; i = "7" }; panelIndex = "7"; type = "visualization"; panelRefName = "panel_7"; embeddableConfig = @{} },
    @{ version = "2.10.0"; gridData = @{ x = 0; y = 24; w = 27; h = 13; i = "8" }; panelIndex = "8"; type = "visualization"; panelRefName = "panel_8"; embeddableConfig = @{} },
    @{ version = "2.10.0"; gridData = @{ x = 27; y = 24; w = 21; h = 13; i = "9" }; panelIndex = "9"; type = "visualization"; panelRefName = "panel_9"; embeddableConfig = @{} },
    @{ version = "2.10.0"; gridData = @{ x = 0; y = 37; w = 48; h = 14; i = "10" }; panelIndex = "10"; type = "search"; panelRefName = "panel_10"; embeddableConfig = @{} },
    @{ version = "2.10.0"; gridData = @{ x = 0; y = 51; w = 48; h = 14; i = "11" }; panelIndex = "11"; type = "search"; panelRefName = "panel_11"; embeddableConfig = @{} },
    @{ version = "2.10.0"; gridData = @{ x = 0; y = 65; w = 48; h = 13; i = "12" }; panelIndex = "12"; type = "search"; panelRefName = "panel_12"; embeddableConfig = @{} }
)

$references = @(
    @{ name = "panel_1"; id = "ai-soc-command-header"; type = "visualization" },
    @{ name = "panel_2"; id = "ai-soc-kpi-triage"; type = "visualization" },
    @{ name = "panel_3"; id = "ai-soc-kpi-incidents"; type = "visualization" },
    @{ name = "panel_4"; id = "ai-soc-kpi-plans"; type = "visualization" },
    @{ name = "panel_5"; id = "ai-soc-kpi-pending"; type = "visualization" },
    @{ name = "panel_6"; id = "ai-soc-event-timeline"; type = "visualization" },
    @{ name = "panel_7"; id = "ai-soc-severity-donut"; type = "visualization" },
    @{ name = "panel_8"; id = "ai-soc-action-types"; type = "visualization" },
    @{ name = "panel_9"; id = "ai-soc-approval-donut"; type = "visualization" },
    @{ name = "panel_10"; id = "ai-soc-incident-feed"; type = "search" },
    @{ name = "panel_11"; id = "ai-soc-response-actions"; type = "search" },
    @{ name = "panel_12"; id = "ai-soc-response-plans"; type = "search" }
)

Save-SavedObject -Type "dashboard" -Id "ai-soc-ollama-response" -Attributes @{
    title = "AI SOC - Ollama Response"
    description = "Visual Wazuh event, Ollama triage, and response command center"
    hits = 0
    panelsJSON = ($panels | ConvertTo-Json -Depth 30 -Compress)
    optionsJSON = (@{ useMargins = $true; hidePanelTitles = $false } | ConvertTo-Json -Compress)
    version = 1
    timeRestore = $true
    timeFrom = "now-24h"
    timeTo = "now"
    refreshInterval = @{ pause = $false; value = 30000 }
    kibanaSavedObjectMeta = @{ searchSourceJSON = '{"query":{"query":"","language":"kuery"},"filter":[]}' }
} -References $references

Write-Host "AI SOC dashboard ready: $DashboardUrl/app/dashboards#/view/ai-soc-ollama-response"
