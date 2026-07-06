param()

$ErrorActionPreference = "Stop"

$REPO_ROOT = (git rev-parse --show-toplevel) -replace '/', '\'
$SPEC_DIR = Join-Path $REPO_ROOT ".spec"
$OUTPUT_FILE = Join-Path $REPO_ROOT "spec-dashboard.html"

function Get-FrontmatterField {
    param([string]$File, [string]$Field)
    if (-not (Test-Path $File)) { return "" }
    $inFrontmatter = $false
    $foundStart = $false
    foreach ($line in [System.IO.File]::ReadAllLines($File)) {
        if ($line -match '^\-\-\-\s*$') {
            if (-not $foundStart) { $foundStart = $true; $inFrontmatter = $true; continue }
            else { break }
        }
        if ($inFrontmatter -and ($line -match "^${Field}:\s*(.*)")) {
            $val = $Matches[1].Trim()
            $val = $val -replace '^"', '' -replace '"$', ''
            $val = $val -replace '\s+#.*$', ''
            $val = $val.Trim()
            return $val
        }
    }
    return ""
}

function Get-MetaField {
    param([string]$File, [string]$Field)
    if (-not (Test-Path $File)) { return "" }
    foreach ($line in [System.IO.File]::ReadAllLines($File)) {
        if ($line -match '^\s*#') { continue }
        if ($line -match "^${Field}:\s*(.*)") {
            $val = $Matches[1].Trim()
            $val = $val -replace '^"', '' -replace '"$', ''
            $val = $val -replace '\s+#.*$', ''
            $val = $val.Trim()
            return $val
        }
    }
    return ""
}

function Get-PrUrls {
    param([string]$File)
    if (-not (Test-Path $File)) { return "" }
    $inCompletion = $false
    $inPrs = $false
    $urls = @()
    foreach ($line in [System.IO.File]::ReadAllLines($File)) {
        if ($line -match '^\s*#') { continue }
        if ($line -match '^completion:') { $inCompletion = $true; continue }
        if ($inCompletion -and ($line -match '^\s+pull_requests:')) { $inPrs = $true; continue }
        if ($inPrs) {
            if ($line -match '^\s*-\s+(.*)') {
                $url = $Matches[1].Trim()
                $url = $url -replace '^"', '' -replace '"$', ''
                $urls += $url
            }
            elseif ($line -notmatch '^\s') { break }
        }
    }
    return ($urls -join "|")
}

function ConvertTo-JsonString {
    param([string]$s)
    $s = $s -replace '\\', '\\'
    $s = $s -replace '"', '\"'
    $s = $s -replace "`n", '\n'
    $s = $s -replace "`r", ''
    return $s
}

$jsonEntries = @()

if (Test-Path $SPEC_DIR) {
    $specDirs = Get-ChildItem -Path $SPEC_DIR -Directory | Where-Object { $_.Name -like "SPEC-*" } | Sort-Object Name
    foreach ($specPath in $specDirs) {
        $specFile = Join-Path $specPath.FullName "spec.md"
        $metaFile = Join-Path $specPath.FullName "meta.yaml"

        $id = Get-FrontmatterField -File $specFile -Field "id"
        $title = Get-FrontmatterField -File $specFile -Field "title"
        $category = Get-FrontmatterField -File $specFile -Field "category"
        $owner = Get-FrontmatterField -File $specFile -Field "owner"
        $status = Get-MetaField -File $metaFile -Field "status"
        $created = Get-MetaField -File $metaFile -Field "created"
        $updated = Get-MetaField -File $metaFile -Field "updated"
        $prUrls = Get-PrUrls -File $metaFile

        if (-not $id) { $id = "unknown" }
        if (-not $title) { $title = "unknown" }
        if (-not $category) { $category = "unknown" }
        if (-not $owner) { $owner = "unknown" }
        if (-not $status) { $status = "unknown" }

        $entry = '{"id":"' + (ConvertTo-JsonString $id) + '","title":"' + (ConvertTo-JsonString $title) + '","category":"' + (ConvertTo-JsonString $category) + '","status":"' + (ConvertTo-JsonString $status) + '","owner":"' + (ConvertTo-JsonString $owner) + '","created":"' + (ConvertTo-JsonString $created) + '","updated":"' + (ConvertTo-JsonString $updated) + '","prs":"' + (ConvertTo-JsonString $prUrls) + '"}'
        $jsonEntries += $entry
    }
}

$jsonArray = "[" + ($jsonEntries -join ",") + "]"

$staticHtmlTop = @'
<!DOCTYPE html>
<html lang="en" data-theme="auto">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Spec Status Dashboard</title>
<style>
:root {
  --bg: #ffffff; --bg-card: #f8f9fa; --text: #1a1a2e; --text-muted: #6c757d;
  --border: #dee2e6; --accent: #4361ee; --accent-light: #eef0ff;
  --badge-feature: #4361ee; --badge-feature-bg: #eef0ff;
  --badge-bug: #e63946; --badge-bug-bg: #fde8ea;
  --badge-refactoring: #f4a261; --badge-refactoring-bg: #fef3e6;
  --badge-testing: #2a9d8f; --badge-testing-bg: #e6f5f3;
  --badge-done: #2a9d8f; --badge-done-bg: #e6f5f3;
  --badge-in_progress: #4361ee; --badge-in_progress-bg: #eef0ff;
  --badge-ready: #7209b7; --badge-ready-bg: #f3e8ff;
  --badge-draft: #6c757d; --badge-draft-bg: #f0f0f0;
  --badge-research: #f4a261; --badge-research-bg: #fef3e6;
  --badge-blocked: #e63946; --badge-blocked-bg: #fde8ea;
  --badge-cancelled: #6c757d; --badge-cancelled-bg: #f0f0f0;
  --badge-superseded: #6c757d; --badge-superseded-bg: #f0f0f0;
  --badge-unknown: #6c757d; --badge-unknown-bg: #f0f0f0;
  --hover-bg: #f0f2ff; --shadow: rgba(0,0,0,0.06);
  --chart-text: #1a1a2e; --chart-center: #ffffff;
}
[data-theme="dark"] {
  --bg: #0f0f1a; --bg-card: #1a1a2e; --text: #e8e8f0; --text-muted: #8888a0;
  --border: #2a2a40; --accent: #6d83f2; --accent-light: #1e2240;
  --badge-feature: #6d83f2; --badge-feature-bg: #1e2240;
  --badge-bug: #ff6b6b; --badge-bug-bg: #2e1215;
  --badge-refactoring: #ffc078; --badge-refactoring-bg: #2e2010;
  --badge-testing: #63e6be; --badge-testing-bg: #102e28;
  --badge-done: #63e6be; --badge-done-bg: #102e28;
  --badge-in_progress: #6d83f2; --badge-in_progress-bg: #1e2240;
  --badge-ready: #b197fc; --badge-ready-bg: #201530;
  --badge-draft: #8888a0; --badge-draft-bg: #252530;
  --badge-research: #ffc078; --badge-research-bg: #2e2010;
  --badge-blocked: #ff6b6b; --badge-blocked-bg: #2e1215;
  --badge-cancelled: #8888a0; --badge-cancelled-bg: #252530;
  --badge-superseded: #8888a0; --badge-superseded-bg: #252530;
  --badge-unknown: #8888a0; --badge-unknown-bg: #252530;
  --hover-bg: #1e2240; --shadow: rgba(0,0,0,0.3);
  --chart-text: #e8e8f0; --chart-center: #0f0f1a;
}
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  background: var(--bg); color: var(--text); line-height: 1.5; padding: 2rem;
}
.header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 2rem; }
.header h1 { font-size: 1.5rem; font-weight: 700; }
.header .subtitle { color: var(--text-muted); font-size: 0.875rem; margin-top: 0.25rem; }
.theme-toggle {
  background: var(--bg-card); border: 1px solid var(--border); border-radius: 8px;
  padding: 0.5rem 0.75rem; cursor: pointer; font-size: 1.1rem; color: var(--text);
  transition: background 0.2s;
}
.theme-toggle:hover { background: var(--hover-bg); }
.charts { display: flex; gap: 2rem; margin-bottom: 2rem; flex-wrap: wrap; }
.chart-card {
  background: var(--bg-card); border: 1px solid var(--border); border-radius: 12px;
  padding: 1.25rem; flex: 1; min-width: 220px; text-align: center;
  box-shadow: 0 1px 3px var(--shadow);
}
.chart-card h3 { font-size: 0.875rem; color: var(--text-muted); margin-bottom: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em; }
.chart-card svg { display: block; margin: 0 auto; }
.chart-legend { display: flex; flex-wrap: wrap; gap: 0.5rem; justify-content: center; margin-top: 0.75rem; }
.legend-item { display: flex; align-items: center; gap: 0.3rem; font-size: 0.75rem; color: var(--text-muted); }
.legend-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.controls { display: flex; gap: 1rem; margin-bottom: 1.5rem; flex-wrap: wrap; align-items: center; }
.filter-group { display: flex; gap: 0.25rem; flex-wrap: wrap; }
.filter-btn {
  background: var(--bg-card); border: 1px solid var(--border); border-radius: 6px;
  padding: 0.375rem 0.75rem; cursor: pointer; font-size: 0.8125rem; color: var(--text);
  transition: all 0.15s;
}
.filter-btn:hover { background: var(--hover-bg); }
.filter-btn.active { background: var(--accent); color: #fff; border-color: var(--accent); }
.search-box {
  flex: 1; min-width: 200px; padding: 0.5rem 0.75rem; border: 1px solid var(--border);
  border-radius: 8px; font-size: 0.875rem; background: var(--bg-card); color: var(--text);
  outline: none; transition: border-color 0.2s;
}
.search-box:focus { border-color: var(--accent); }
.search-box::placeholder { color: var(--text-muted); }
.table-wrap {
  background: var(--bg-card); border: 1px solid var(--border); border-radius: 12px;
  overflow: hidden; box-shadow: 0 1px 3px var(--shadow);
}
table { width: 100%; border-collapse: collapse; }
thead th {
  background: var(--bg-card); border-bottom: 2px solid var(--border); padding: 0.75rem 1rem;
  text-align: left; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em;
  color: var(--text-muted); cursor: pointer; user-select: none; white-space: nowrap;
}
thead th:hover { color: var(--text); }
thead th .sort-arrow { margin-left: 0.25rem; opacity: 0.3; }
thead th.sorted .sort-arrow { opacity: 1; }
tbody tr { border-bottom: 1px solid var(--border); transition: background 0.1s; }
tbody tr:last-child { border-bottom: none; }
tbody tr:hover { background: var(--hover-bg); }
td { padding: 0.625rem 1rem; font-size: 0.875rem; vertical-align: middle; }
.spec-id { font-family: "SF Mono", "Cascadia Code", "Fira Code", monospace; font-weight: 600; color: var(--accent); font-size: 0.8125rem; }
.spec-title { font-weight: 500; }
.badge {
  display: inline-block; padding: 0.15rem 0.5rem; border-radius: 10px;
  font-size: 0.75rem; font-weight: 500; white-space: nowrap;
}
.pr-link { color: var(--accent); text-decoration: none; font-size: 0.8125rem; }
.pr-link:hover { text-decoration: underline; }
.empty-state {
  text-align: center; padding: 3rem; color: var(--text-muted); font-size: 1rem;
}
.count-badge {
  background: var(--bg-card); border: 1px solid var(--border); border-radius: 6px;
  padding: 0.25rem 0.5rem; font-size: 0.75rem; color: var(--text-muted);
}
</style>
</head>
<body>
<div class="header">
  <div>
    <h1>Spec Status Dashboard</h1>
    <div class="subtitle">Generated overview of all specs in .spec/</div>
  </div>
  <button class="theme-toggle" id="themeToggle" title="Toggle theme">&#9790;</button>
</div>
<div class="charts" id="chartsContainer"></div>
<div class="controls">
  <div class="filter-group" id="statusFilters">
    <button class="filter-btn active" data-filter="all">All</button>
    <button class="filter-btn" data-filter="open">Open</button>
    <button class="filter-btn" data-filter="done">Done</button>
    <button class="filter-btn" data-filter="blocked">Blocked</button>
  </div>
  <div class="filter-group" id="categoryFilters">
    <button class="filter-btn active" data-filter="all">All types</button>
    <button class="filter-btn" data-filter="feature">Feature</button>
    <button class="filter-btn" data-filter="bug">Bug</button>
    <button class="filter-btn" data-filter="refactoring">Refactoring</button>
    <button class="filter-btn" data-filter="testing">Testing</button>
  </div>
  <input type="text" class="search-box" id="searchBox" placeholder="Search by ID or title...">
  <span class="count-badge" id="countBadge"></span>
</div>
<div class="table-wrap">
  <table>
    <thead>
      <tr>
        <th data-col="id" class="sorted">ID <span class="sort-arrow">&#9660;</span></th>
        <th data-col="title">Title <span class="sort-arrow">&#9650;</span></th>
        <th data-col="category">Category <span class="sort-arrow">&#9650;</span></th>
        <th data-col="status">Status <span class="sort-arrow">&#9650;</span></th>
        <th data-col="owner">Owner <span class="sort-arrow">&#9650;</span></th>
        <th data-col="updated">Updated <span class="sort-arrow">&#9650;</span></th>
        <th>PR</th>
      </tr>
    </thead>
    <tbody id="specTableBody"></tbody>
  </table>
  <div class="empty-state" id="emptyState" style="display:none">No specs found.</div>
</div>
'@

$staticHtmlBottom = @'
<script>
(function() {
  var data = JSON.parse(document.getElementById('spec-data').textContent);

  var OPEN_STATUSES = ['draft','research','ready','in_progress'];
  var DONE_STATUSES = ['done','superseded'];
  var BLOCKED_STATUSES = ['blocked'];
  var CANCELLED_STATUSES = ['cancelled'];

  var STATUS_COLORS = {
    done:'#2a9d8f', in_progress:'#4361ee', ready:'#7209b7', draft:'#6c757d',
    research:'#f4a261', blocked:'#e63946', cancelled:'#6c757d', superseded:'#6c757d', unknown:'#6c757d'
  };
  var CATEGORY_COLORS = {
    feature:'#4361ee', bug:'#e63946', refactoring:'#f4a261', testing:'#2a9d8f', unknown:'#6c757d'
  };
  var OWNER_COLORS = ['#4361ee','#e63946','#2a9d8f','#f4a261','#7209b7','#e76f51','#457b9d','#6d6875'];

  function getStatusGroup(s) {
    s = (s || '').toLowerCase();
    if (DONE_STATUSES.indexOf(s) !== -1) return 'done';
    if (BLOCKED_STATUSES.indexOf(s) !== -1) return 'blocked';
    if (CANCELLED_STATUSES.indexOf(s) !== -1) return 'done';
    return 'open';
  }

  function specNum(id) {
    var m = (id || '').match(/SPEC-(\d+)/);
    return m ? parseInt(m[1], 10) : 0;
  }

  var sortCol = 'id', sortAsc = false;
  var statusFilter = 'all', categoryFilter = 'all', searchTerm = '';

  function countBy(arr, key) {
    var counts = {};
    arr.forEach(function(item) {
      var v = (item[key] || 'unknown').toLowerCase();
      counts[v] = (counts[v] || 0) + 1;
    });
    return counts;
  }

  function countByOwner(arr) {
    var counts = {};
    arr.forEach(function(item) {
      var v = item.owner || 'unknown';
      counts[v] = (counts[v] || 0) + 1;
    });
    return counts;
  }

  function buildDonut(container, title, countsObj, colorMap) {
    var card = document.createElement('div');
    card.className = 'chart-card';
    var h3 = document.createElement('h3');
    h3.textContent = title;
    card.appendChild(h3);

    var entries = [];
    var total = 0;
    for (var k in countsObj) {
      entries.push({label: k, count: countsObj[k]});
      total += countsObj[k];
    }
    entries.sort(function(a, b) { return b.count - a.count; });

    var svgNS = 'http://www.w3.org/2000/svg';
    var svg = document.createElementNS(svgNS, 'svg');
    svg.setAttribute('width', '120');
    svg.setAttribute('height', '120');
    svg.setAttribute('viewBox', '0 0 42 42');

    if (total > 0) {
      var offset = 0;
      entries.forEach(function(e, i) {
        var pct = (e.count / total) * 100;
        var gap = 100 - pct;
        var circle = document.createElementNS(svgNS, 'circle');
        circle.setAttribute('cx', '21');
        circle.setAttribute('cy', '21');
        circle.setAttribute('r', '15.9155');
        circle.setAttribute('fill', 'none');
        circle.setAttribute('stroke-width', '5');
        var color;
        if (typeof colorMap === 'function') { color = colorMap(e.label, i); }
        else { color = colorMap[e.label] || '#6c757d'; }
        circle.setAttribute('stroke', color);
        circle.setAttribute('stroke-dasharray', pct + ' ' + gap);
        circle.setAttribute('stroke-dashoffset', (100 - offset + 25).toString());
        svg.appendChild(circle);
        offset += pct;
      });
    }

    var center = document.createElementNS(svgNS, 'circle');
    center.setAttribute('cx', '21');
    center.setAttribute('cy', '21');
    center.setAttribute('r', '11');
    center.setAttribute('fill', 'var(--chart-center)');
    svg.appendChild(center);

    var txt = document.createElementNS(svgNS, 'text');
    txt.setAttribute('x', '21');
    txt.setAttribute('y', '22.5');
    txt.setAttribute('text-anchor', 'middle');
    txt.setAttribute('font-size', '7');
    txt.setAttribute('font-weight', '700');
    txt.setAttribute('fill', 'var(--chart-text)');
    txt.textContent = total.toString();
    svg.appendChild(txt);

    card.appendChild(svg);

    var legend = document.createElement('div');
    legend.className = 'chart-legend';
    entries.forEach(function(e, i) {
      var item = document.createElement('span');
      item.className = 'legend-item';
      var dot = document.createElement('span');
      dot.className = 'legend-dot';
      var color;
      if (typeof colorMap === 'function') { color = colorMap(e.label, i); }
      else { color = colorMap[e.label] || '#6c757d'; }
      dot.style.background = color;
      item.appendChild(dot);
      item.appendChild(document.createTextNode(e.label + ' (' + e.count + ')'));
      legend.appendChild(item);
    });
    card.appendChild(legend);
    container.appendChild(card);
  }

  function renderCharts() {
    var c = document.getElementById('chartsContainer');
    c.innerHTML = '';
    var statusCounts = countBy(data, 'status');
    var categoryCounts = countBy(data, 'category');
    var ownerCounts = countByOwner(data);
    buildDonut(c, 'By Status', statusCounts, STATUS_COLORS);
    buildDonut(c, 'By Category', categoryCounts, CATEGORY_COLORS);
    var ownerKeys = Object.keys(ownerCounts).sort(function(a,b){ return ownerCounts[b]-ownerCounts[a]; });
    var ownerColorMap = {};
    ownerKeys.forEach(function(k, i) { ownerColorMap[k] = OWNER_COLORS[i % OWNER_COLORS.length]; });
    buildDonut(c, 'By Owner', ownerCounts, ownerColorMap);
  }

  function badgeHtml(val, type) {
    var v = (val || 'unknown').toLowerCase();
    var display = v.replace(/_/g, ' ');
    return '<span class="badge" style="background:var(--badge-' + v + '-bg,var(--badge-unknown-bg));color:var(--badge-' + v + ',var(--badge-unknown))">' + display + '</span>';
  }

  function prHtml(prs) {
    if (!prs) return '';
    return prs.split('|').map(function(url) {
      var m = url.match(/\/pull\/(\d+)/);
      var label = m ? '#' + m[1] : 'PR';
      return '<a class="pr-link" href="' + url + '" target="_blank" rel="noopener">' + label + '</a>';
    }).join(' ');
  }

  function filterAndSort() {
    var filtered = data.filter(function(s) {
      if (statusFilter !== 'all') {
        var g = getStatusGroup(s.status);
        if (g !== statusFilter) return false;
      }
      if (categoryFilter !== 'all') {
        if ((s.category || '').toLowerCase() !== categoryFilter) return false;
      }
      if (searchTerm) {
        var q = searchTerm.toLowerCase();
        var inId = (s.id || '').toLowerCase().indexOf(q) !== -1;
        var inTitle = (s.title || '').toLowerCase().indexOf(q) !== -1;
        if (!inId && !inTitle) return false;
      }
      return true;
    });

    filtered.sort(function(a, b) {
      var va, vb;
      if (sortCol === 'id') { va = specNum(a.id); vb = specNum(b.id); }
      else if (sortCol === 'updated') { va = a.updated || ''; vb = b.updated || ''; }
      else { va = (a[sortCol] || '').toLowerCase(); vb = (b[sortCol] || '').toLowerCase(); }
      var cmp = va < vb ? -1 : (va > vb ? 1 : 0);
      return sortAsc ? cmp : -cmp;
    });

    return filtered;
  }

  function render() {
    var filtered = filterAndSort();
    var tbody = document.getElementById('specTableBody');
    var empty = document.getElementById('emptyState');
    var countBadge = document.getElementById('countBadge');

    countBadge.textContent = filtered.length + ' of ' + data.length + ' specs';

    if (filtered.length === 0) {
      tbody.innerHTML = '';
      empty.style.display = 'block';
      return;
    }
    empty.style.display = 'none';

    var html = '';
    filtered.forEach(function(s) {
      html += '<tr>'
        + '<td class="spec-id">' + (s.id || 'unknown') + '</td>'
        + '<td class="spec-title">' + (s.title || 'unknown') + '</td>'
        + '<td>' + badgeHtml(s.category) + '</td>'
        + '<td>' + badgeHtml(s.status) + '</td>'
        + '<td style="color:var(--text-muted)">' + (s.owner || 'unknown') + '</td>'
        + '<td style="color:var(--text-muted)">' + (s.updated || '') + '</td>'
        + '<td>' + prHtml(s.prs) + '</td>'
        + '</tr>';
    });
    tbody.innerHTML = html;
  }

  // Theme
  function getPreferredTheme() {
    var stored = localStorage.getItem('spec-dashboard-theme');
    if (stored) return stored;
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  }
  function applyTheme(t) {
    document.documentElement.setAttribute('data-theme', t);
    document.getElementById('themeToggle').textContent = t === 'dark' ? '\u2600' : '\u263E';
  }
  applyTheme(getPreferredTheme());
  document.getElementById('themeToggle').addEventListener('click', function() {
    var current = document.documentElement.getAttribute('data-theme');
    var next = current === 'dark' ? 'light' : 'dark';
    localStorage.setItem('spec-dashboard-theme', next);
    applyTheme(next);
  });

  // Filters
  document.getElementById('statusFilters').addEventListener('click', function(e) {
    if (e.target.classList.contains('filter-btn')) {
      this.querySelectorAll('.filter-btn').forEach(function(b) { b.classList.remove('active'); });
      e.target.classList.add('active');
      statusFilter = e.target.getAttribute('data-filter');
      render();
    }
  });
  document.getElementById('categoryFilters').addEventListener('click', function(e) {
    if (e.target.classList.contains('filter-btn')) {
      this.querySelectorAll('.filter-btn').forEach(function(b) { b.classList.remove('active'); });
      e.target.classList.add('active');
      categoryFilter = e.target.getAttribute('data-filter');
      render();
    }
  });
  document.getElementById('searchBox').addEventListener('input', function() {
    searchTerm = this.value;
    render();
  });

  // Sort
  document.querySelectorAll('thead th[data-col]').forEach(function(th) {
    th.addEventListener('click', function() {
      var col = this.getAttribute('data-col');
      if (sortCol === col) { sortAsc = !sortAsc; }
      else { sortCol = col; sortAsc = true; }
      document.querySelectorAll('thead th').forEach(function(h) { h.classList.remove('sorted'); });
      this.classList.add('sorted');
      this.querySelector('.sort-arrow').textContent = sortAsc ? '\u25B2' : '\u25BC';
      render();
    });
  });

  renderCharts();
  render();
})();
</script>
</body>
</html>
'@

$dataIsland = '<script type="application/json" id="spec-data">' + "`n" + $jsonArray + "`n" + '</script>'

$fullHtml = $staticHtmlTop + "`n" + $dataIsland + "`n" + $staticHtmlBottom

[System.IO.File]::WriteAllText($OUTPUT_FILE, $fullHtml, [System.Text.UTF8Encoding]::new($false))

Write-Host "Dashboard generated at $OUTPUT_FILE"
