# ============================================================
#  PRV 文件重组脚本  v1.1
#  使用方法：
#    预览：  powershell -ExecutionPolicy Bypass -File Reorganize-PRV.ps1 -WhatIf
#    执行：  powershell -ExecutionPolicy Bypass -File Reorganize-PRV.ps1
# ============================================================
param([switch]$WhatIf)
$ErrorActionPreference = "Continue"
$base  = "F:\PRV"
$pnet  = "$base\PNetGimini"
$met   = "$pnet\Method"
$trace = "$base\TraceClaw"
$moved = 0; $skip = 0

$dirs = @(
    "$pnet\01_Patent\Final",
    "$pnet\01_Patent\History",
    "$pnet\01_Patent\Defense",
    "$pnet\02_MathTheory\Annotated",
    "$pnet\02_MathTheory\ForMathWorker",
    "$pnet\02_MathTheory\ModelHistory",
    "$pnet\02_MathTheory\ResearchStatus",
    "$pnet\03_Architecture\FSNetEngine",
    "$pnet\03_Architecture\DigitalTwin",
    "$pnet\03_Architecture\Product",
    "$pnet\03_Architecture\AI",
    "$pnet\04_Engineering\Calibration",
    "$pnet\04_Engineering\AsyncStream",
    "$pnet\04_Engineering\Modelica",
    "$pnet\05_Roadmap",
    "$pnet\06_Minutes\Iterations",
    "$pnet\06_Minutes\LBM",
    "$pnet\06_Minutes\Stages",
    "$pnet\07_ModelHistory",
    "$pnet\08_Business",
    "$pnet\09_Images",
    "$pnet\10_Paper",
    "$trace\00_Charter",
    "$trace\01_CDMT",
    "$trace\02_Skills",
    "$trace\03_Discussions"
)

# 创建目录
foreach ($d in $dirs) {
    if ($WhatIf) { Write-Host "[mkdir] $d" -ForegroundColor Cyan }
    else { New-Item -ItemType Directory -Path $d -Force | Out-Null }
}

function Mv($src, $dst) {
    if (-not (Test-Path $src)) {
        Write-Host "  [skip-missing] $(Split-Path $src -Leaf)" -ForegroundColor DarkGray
        $script:skip++; return
    }
    if ($WhatIf) {
        Write-Host "  [move] $($src.Replace($base,'')) -> $($dst.Replace($base,''))" -ForegroundColor Cyan
        return
    }
    $dstDir = Split-Path $dst -Parent
    if (-not (Test-Path $dstDir)) { New-Item -ItemType Directory -Path $dstDir -Force | Out-Null }
    if (Test-Path $dst) {
        Write-Host "  [skip-exists] $(Split-Path $dst -Leaf)" -ForegroundColor Yellow
        $script:skip++
    } else {
        Move-Item -Path $src -Destination $dst -Force
        Write-Host "  [ok] $(Split-Path $dst -Leaf)" -ForegroundColor Green
        $script:moved++
    }
}

function MvGlob($dir, $pat, $dst) {
    Get-ChildItem -Path $dir -Filter $pat -ErrorAction SilentlyContinue | ForEach-Object {
        Mv $_.FullName "$dst\$($_.Name)"
    }
}

function MvDir($srcDir, $dstDir) {
    Get-ChildItem -Path $srcDir -File -ErrorAction SilentlyContinue | ForEach-Object {
        Mv $_.FullName "$dstDir\$($_.Name)"
    }
}

Write-Host "`n=== [1] 专利 IP ===" -ForegroundColor White
$patentFinal = @("ABSTRACT.docx","ABSTRACT.pdf","CLAIMS.docx","CLAIMS.pdf",
    "Description.docx","Description.pdf","Drawings.docx","Drawings.pdf",
    "Figures.docx","Figures.pdf",
    "PRV_Final_Patent_Application.docx.docx",
    "PRV_Final_Submission_PNetGimini.docx.docx",
    "PRV_Final_Submission_PNetGimini.docx.pdf",
    "se-wolf-receipt.pdf")
foreach ($f in $patentFinal) { Mv "$pnet\$f" "$pnet\01_Patent\Final\$f" }

$patentDef = @("10专利技术交底书.docx",
    "10专利技术交底书和权利要求书.docx","21答辩.docx")
foreach ($f in $patentDef) { Mv "$pnet\$f" "$pnet\01_Patent\Defense\$f" }

$histSrc = "$pnet\交底书不同版本"
if (Test-Path $histSrc) {
    MvDir $histSrc "$pnet\01_Patent\History"
    if (-not $WhatIf) { Remove-Item $histSrc -Force -Recurse -ErrorAction SilentlyContinue }
}

Write-Host "`n=== [2] 数学理论 ===" -ForegroundColor White
MvGlob $met "PNetGimini_数学理论注释版*" "$pnet\02_MathTheory\Annotated"
MvGlob $met "PNetGimini_致数学工作者*"       "$pnet\02_MathTheory\ForMathWorker"
Mv "$met\PNetGimini_模型演变历史_v1.0.docx" "$pnet\02_MathTheory\ModelHistory\PNetGimini_模型演变历史_v1.0.docx"
Mv "$met\模型演变历史说明.txt"       "$pnet\02_MathTheory\ModelHistory\模型演变历史说明.txt"
$res = @("30国际研究现状系统解析.docx",
    "深度研究：FS_net 框架的文献支撑.docx",
    "深度研究：FS_net 物理栈的五层耦合与防御设计.docx")
foreach ($f in $res) {
    Mv "$met\$f"  "$pnet\02_MathTheory\ResearchStatus\$f"
    Mv "$pnet\$f" "$pnet\02_MathTheory\ResearchStatus\$f"
}

Write-Host "`n=== [3] 系统架构 ===" -ForegroundColor White
Mv "$met\PNetGimini_FSNetEngine代码架构_v1.0.docx" "$pnet\03_Architecture\FSNetEngine\PNetGimini_FSNetEngine代码架构_v1.0.docx"

$dt = @("PNetGimini_数字孪生讨论_v1.0.docx",
    "PNetGimini_数字孪生构想_v1.0.html",
    "PNetGimini_数字孪生构想_v1.0.pdf",
    "基于PNetGimini的数字孪生网络构想——AI增强的物理场引擎架构.docx")
foreach ($f in $dt) { Mv "$met\$f" "$pnet\03_Architecture\DigitalTwin\$f" }

Mv "$met\PNetGimini_OpenClaw产品架构_v1.0.docx" "$pnet\03_Architecture\Product\PNetGimini_OpenClaw产品架构_v1.0.docx"

$ai = @("PNetGimini_AI引入模型讨论_v1.0.docx",
    "5.AI增强的四大进阶方向.docx")
foreach ($f in $ai) { Mv "$met\$f" "$pnet\03_Architecture\AI\$f" }
Mv "$pnet\4.系统架构预演.docx" "$pnet\03_Architecture\AI\4.系统架构预演.docx"

Write-Host "`n=== [4] 工程实现 ===" -ForegroundColor White
Mv "$met\PNetGimini_参数标定方案_v1.0.docx"   "$pnet\04_Engineering\Calibration\PNetGimini_参数标定方案_v1.0.docx"
Mv "$met\PNetGimini_异步流步方案决策_v1.0.docx" "$pnet\04_Engineering\AsyncStream\PNetGimini_异步流步方案决策_v1.0.docx"
Mv "$met\PNetGimini_Modelica引入讨论_v1.0.docx"       "$pnet\04_Engineering\Modelica\PNetGimini_Modelica引入讨论_v1.0.docx"

Write-Host "`n=== [5] 技术规划 ===" -ForegroundColor White
$road = @("PNetGimini_V3_V4技术路线图_v1.0.docx",
    "PNetGimini_CAE知识库_v1.0.docx")
foreach ($f in $road) { Mv "$met\$f" "$pnet\05_Roadmap\$f" }
Mv "$pnet\32行动路线图.docx" "$pnet\05_Roadmap\32行动路线图.docx"

Write-Host "`n=== [6] 讨论纪要 ===" -ForegroundColor White
$stages = @("PNetGimini_V3.0阶段深化讨论纪要_v1.0.docx",
    "PNetGimini_V3.0阶段深化讨论纪要_v1.1.docx",
    "PNetGimini_技术路线阶段讨论纪要_V0.1.docx")
foreach ($f in $stages) { Mv "$met\$f" "$pnet\06_Minutes\Stages\$f" }

MvGlob $met "discussion_PNetGimini_*.html" "$pnet\06_Minutes\Iterations"
MvGlob $met "discussion_PNetGimini_*.md"   "$pnet\06_Minutes\Iterations"
MvGlob $met "discussion_PNetGimini_*.pdf"  "$pnet\06_Minutes\Iterations"

$lbm = @("LBM的讨论.txt","0310LBM基础理论讨论","LBM3.0细化讨论")
foreach ($f in $lbm) { Mv "$met\$f" "$pnet\06_Minutes\LBM\$f" }

Write-Host "`n=== [7] 模型历史 ===" -ForegroundColor White
$hist = @(
    "1.0力热耦合模型说明文稿.docx",
    "1.0 基于拉格朗日乘子区域分解法的网络配置自适应部署理论与方法（图公式）.docx",
    "1.1基于温度场拉格朗日乘子区域分解法的网络配置自适应部署理论与方法.docx",
    "1.2PNetGimini^7一种基于物理感知域分解（显式温度场）的网络配置确定性部署理论框架.docx",
    "1.2PNetGimini：一种基于物理感知域分解（显式温度场）的网络配置确定性部署理论框架.docx",
    "1.基于拉格朗日乘子区域分解法的网络配置自适应部署理论与方法（完全版）.docx",
    "基于拉格朗日乘子区域分解法的网络配置自适应部署理论与方法.docx",
    "PNetGimini_六场模型_v1.2.html",
    "PNetGimini_六场模型_v1.2.pdf",
    "PNetGimini_六场模型_v1.3.pdf",
    "PNetGimini_6field_model_v1.2.html",
    "PNetGimini六场模型——数学-工程框架与实施路线图.docx")
foreach ($f in $hist) { Mv "$met\$f" "$pnet\07_ModelHistory\$f" }
$hist2 = @("2.从网络问题到数学模型的映射过程.docx",
    "3.模型统一与合理性验证.docx")
foreach ($f in $hist2) { Mv "$pnet\$f" "$pnet\07_ModelHistory\$f" }

Write-Host "`n=== [8] 战略商业 ===" -ForegroundColor White
$biz = @("6.战略规划与技术白皮书.docx",
    "7.未来市场分析.docx",
    "8.商业路线图.docx",
    "31创新点梳理.docx")
foreach ($f in $biz) { Mv "$pnet\$f" "$pnet\08_Business\$f" }

Write-Host "`n=== [9] 图片素材 ===" -ForegroundColor White
foreach ($f in @("1.png","2.png","3.png","logo.png")) {
    Mv "$pnet\$f" "$pnet\09_Images\$f"
}
MvGlob $pnet "4.*工作流*.png" "$pnet\09_Images"
MvGlob $met  "0311GLBM*.png"              "$pnet\09_Images"

Write-Host "`n=== [10] 论文 ===" -ForegroundColor White
$paperSrc = "$pnet\paper"
if (Test-Path $paperSrc) {
    MvDir $paperSrc "$pnet\10_Paper"
    if (-not $WhatIf) { Remove-Item $paperSrc -Force -Recurse -ErrorAction SilentlyContinue }
}

Write-Host "`n=== [11] TraceClaw ===" -ForegroundColor White
Mv "$met\PNetGimini_CDMT_训练素材库_v1.0.docx" "$trace\01_CDMT\PNetGimini_CDMT_训练素材库_v1.0.docx"
$oldTrace = "$base\跨领域数学源源法的Skill设计"
if (Test-Path $oldTrace) {
    MvDir $oldTrace "$trace\03_Discussions"
    if (-not $WhatIf) { Write-Host "  [请手动删除旧文件夹] $oldTrace" -ForegroundColor Yellow }
}

Write-Host "`n============================================" -ForegroundColor White
if ($WhatIf) {
    Write-Host "  [预览模式] 未实际执行。确认无误后去掉 -WhatIf 重新运行。" -ForegroundColor Cyan
} else {
    Write-Host "  完成！ 移动: $moved  跳过: $skip" -ForegroundColor Green
}
Write-Host "============================================`n" -ForegroundColor White
