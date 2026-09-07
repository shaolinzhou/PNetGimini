import os
import shutil
import glob
from pathlib import Path

# ================= 配置区域 =================
BASE_DIR = r"F:\PRV"
PNET = os.path.join(BASE_DIR, "PNetGimini")
MET = os.path.join(PNET, "Method")
TRACE = os.path.join(BASE_DIR, "TraceClaw")

stats = {"success": 0, "exist": 0, "error": 0}

def mv(src, dst):
    """直接执行移动逻辑"""
    src_path = Path(src)
    dst_path = Path(dst)
    
    if not src_path.exists():
        return

    # 自动创建目标父目录
    dst_path.parent.mkdir(parents=True, exist_ok=True)

    if dst_path.exists():
        print(f"[跳过] 目标已存在: {dst_path.name}")
        stats["exist"] += 1
    else:
        try:
            # 使用 shutil.move 跨文件夹移动
            shutil.move(str(src_path), str(dst_path))
            print(f"[成功] 移动: {src_path.name}")
            stats["success"] += 1
        except Exception as e:
            print(f"[错误] 无法操作 {src_path.name}: {e}")
            stats["error"] += 1

def mv_glob(src_dir, pattern, dst_dir):
    """通配符批量移动"""
    if not os.path.exists(src_dir): return
    for f in glob.glob(os.path.join(src_dir, pattern)):
        mv(f, os.path.join(dst_dir, os.path.basename(f)))

# ================= 执行重构 =================
print(f"正在重构目录结构: {BASE_DIR} ...")

# 1. 专利 IP (Final & Defense)
patent_final = ["ABSTRACT.docx", "ABSTRACT.pdf", "CLAIMS.docx", "CLAIMS.pdf", 
                "Description.docx", "Description.pdf", "Drawings.docx", "Drawings.pdf", 
                "Figures.docx", "Figures.pdf", "se-wolf-receipt.pdf"]
for f in patent_final:
    mv(os.path.join(PNET, f), os.path.join(PNET, "01_Patent", "Final", f))

mv_glob(PNET, "*专利技术交底书*", os.path.join(PNET, "01_Patent", "Defense"))
mv_glob(MET, "*专利技术交底书*", os.path.join(PNET, "01_Patent", "Defense"))

# 2. 数学理论
mv_glob(PNET, "*理论注释版*", os.path.join(PNET, "02_MathTheory", "Annotated"))
mv_glob(PNET, "*数学工作者*", os.path.join(PNET, "02_MathTheory", "ForMathWorker"))
mv_glob(MET, "*模型演变历史*", os.path.join(PNET, "02_MathTheory", "ModelHistory"))
mv_glob(MET, "*研究现状*", os.path.join(PNET, "02_MathTheory", "ResearchStatus"))

# 3. 系统架构
mv_glob(MET, "*FSNetEngine代码架构*", os.path.join(PNET, "03_Architecture", "FSNetEngine"))
mv_glob(MET, "*数字孪生*", os.path.join(PNET, "03_Architecture", "DigitalTwin"))
mv_glob(MET, "*OpenClaw产品架构*", os.path.join(PNET, "03_Architecture", "Product"))
mv_glob(MET, "*AI增强*", os.path.join(PNET, "03_Architecture", "AI"))
mv(os.path.join(PNET, "4.系统架构预演.docx"), os.path.join(PNET, "03_Architecture", "AI", "4.系统架构预演.docx"))

# 4. 讨论纪要
mv_glob(PNET, "*_V1_to_V2*", os.path.join(PNET, "06_Minutes", "Iterations"))
mv_glob(MET, "*LBM*", os.path.join(PNET, "06_Minutes", "LBM"))
mv_glob(MET, "*阶段讨论纪要*", os.path.join(PNET, "06_Minutes", "Stages"))

# 5. 其他分类 (Roadmap & Business & Images)
mv_glob(MET, "*技术路线图*", os.path.join(PNET, "05_Roadmap"))
mv(os.path.join(PNET, "32行动路线图.docx"), os.path.join(PNET, "05_Roadmap", "32行动路线图.docx"))
mv_glob(PNET, "*战略规划*", os.path.join(PNET, "08_Business"))
mv_glob(PNET, "*.png", os.path.join(PNET, "09_Images"))

# 6. TraceClaw
mv(os.path.join(MET, "PNetGimini_TraceClaw核心章程_v1.0.docx"), os.path.join(TRACE, "00_Charter", "PNetGimini_TraceClaw核心章程_v1.0.docx"))
mv_glob(MET, "*CDMT*", os.path.join(TRACE, "01_CDMT"))
mv_glob(MET, "*Skills*", os.path.join(TRACE, "02_Skills"))

print(f"\n操作完成! 成功移动: {stats['success']}, 目标已存在: {stats['exist']}, 错误: {stats['error']}")