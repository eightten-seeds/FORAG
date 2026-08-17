"""Create the deterministic Candidate Golden Dataset for frozen kb_v1."""
from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHUNKS = ROOT / "data/processed/chunks.jsonl"
DATASET = ROOT / "data/evaluation/golden_dataset.jsonl"
REVIEW = ROOT / "data/evaluation/golden_review.csv"
KB_VERSION = "kb_v1"


def sample(question: str, answer: str, chunk_ids: list[str], category: str, split: str) -> dict[str, object]:
    return {"question": question, "gt_answer": answer, "gold_chunk_ids": chunk_ids, "category": category, "kb_version": KB_VERSION, "split": split}


CANDIDATES = [
    sample("GORE-TEX 外套机洗时，水温和洗涤剂应该怎么选？", "先遵循衣物洗标；GORE-TEX 衣物可用温水（105°F/40°C）机洗，并使用少量液体洗涤剂。不要使用洗衣粉、柔顺剂或含氯漂白剂。", ["goretex-outerwear-001/what-s-the-best-way-to-wash-my-gore-tex-garment/004"], "washing", "dev"),
    sample("我的冲锋衣有泥土、篝火烟味或做饭留下的气味，需要多久洗一次？", "按需要清洗；当需要去除泥土、篝火烟味或烹饪气味等污物时就可以清洗。洗涤、干燥和加热也有助于恢复 DWR。", ["goretex-outerwear-001/how-often-should-i-wash-my-gore-tex-garment/005"], "washing", "dev"),
    sample("我的洗衣机没有免烫防皱程序，GORE-TEX 外套应该选什么模式？", "使用不会强力甩干的轻柔模式；将转速降至 400 rpm 或以下可减少褶皱。", ["goretex-outerwear-001/what-cycle-do-i-use-if-my-washing-machine-doesn-t-have-a-permanent-press-setting/006"], "washing", "dev"),
    sample("Can I bleach a GORE-TEX jacket?", "No. GORE-TEX advises against bleach because it can affect the garment’s colour and performance.", ["goretex-outerwear-001/can-i-use-bleach/010"], "washing", "test"),
    sample("DWR 到底是什么，为什么水珠会在外层滚落？", "DWR 是耐久防泼水处理，会让水在衣物外层形成水珠并滚落，而不是被表层吸收。", ["goretex-outerwear-001/what-is-dwr/011"], "dwr", "dev"),
    sample("不挂水珠是不是说明 GORE-TEX 已经漏水了？", "不一定。DWR 失效时水不再成珠，需要通过洗涤加热重新激活或重新施加；产品仍会防水，但舒适性可能下降。", ["goretex-dwr-001/wash-care-reactivate/001"], "dwr", "dev"),
    sample("Can I use an aerosol spray to restore DWR?", "Technically yes, but GORE-TEX recommends a pump-action spray rather than an aerosol spray to reduce environmental impact.", ["goretex-outerwear-001/can-i-use-an-aerosol-dwr-spray-to-replenish-the-dwr/012"], "dwr", "test"),
    sample("Mammut 硬壳洗之前要做哪些准备？", "先查看洗标；清空口袋、拉好拉链、扣好按钮和绑带、固定魔术贴、松开抽绳，抖掉灰尘后把夹克翻到里面。", ["mammut-hardshell-001/step-1-prep/001"], "hardshell_washing", "dev"),
    sample("硬壳衣能用柔顺剂或漂白剂吗？", "不能。Mammut 建议使用运动服环保液体洗涤剂，并避免洗衣粉、漂白剂、去渍剂和柔顺剂。", ["mammut-hardshell-001/step-2-detergent/002"], "hardshell_washing", "dev"),
    sample("How should I wash a Mammut hardshell?", "Machine wash cold at up to 30°C/85°F, ideally with an extra rinse and low spin; use a delicate cycle if those settings are unavailable.", ["mammut-hardshell-001/step-3-how-to-wash-hardshells/003"], "hardshell_washing", "dev"),
    sample("硬壳洗完怎么烘干才能重新激活防泼水？", "先正面朝外晾干；完全干后，在不超过 55°C/125°F 的条件下滚筒烘约 20 分钟以激活 DWR。", ["mammut-hardshell-001/step-4-how-to-dry-hardshells/004"], "hardshell_drying", "dev"),
    sample("我把硬壳烘过了还是不挂水珠，该怎么办？", "如果烘干激活 DWR 后仍不成珠，可使用环保浸渍喷雾，并按瓶身说明在户外重点处理肩部等高磨损区域。", ["mammut-hardshell-001/step-5-waterproofing/005"], "dwr", "dev"),
    sample("羽绒服用什么洗涤剂，哪些东西要避开？", "建议用环保羽绒专用洗涤剂；避免洗衣粉、漂白剂和柔顺剂。", ["mammut-down-001/step-2-detergent/002"], "down_washing", "dev"),
    sample("羽绒服洗完能放暖气片或太阳下晒吗？", "不建议。可翻面平铺，用干净毛巾轻压和滚动吸走水分；不要放在暖气片上或阳光下晾晒。", ["mammut-down-001/step-4-dry-with-a-towel/004"], "down_drying", "dev"),
    sample("Why do dryer balls help when drying a down jacket?", "Mammut recommends low tumble drying with three dryer balls or clean tennis balls to prevent down from clumping, and the jacket should be fully dry before removal.", ["mammut-down-001/step-5-tumble-dry/005"], "down_drying", "dev"),
    sample("Mammut 羽绒服是不是越勤洗越好？", "不是。Mammut 的建议是尽量不要每年完整清洗羽绒服超过一次。", ["mammut-down-001/tips/007"], "down_washing", "dev"),
    sample("Softshell 要用什么程序洗？", "Mammut 建议 softshell 在最高 30°C/85°F 的冷水中使用正常洗涤程序。", ["mammut-softshell-001/step-3-how-to-wash-softshells/003"], "softshell", "test"),
    sample("软壳衣能不能烘干？防泼水怎么恢复？", "不要滚筒烘干，应避开直射阳光晾干；要激活 DWR，可隔着布以最高 110°C 熨烫。", ["mammut-softshell-001/step-4-how-to-dry-softshells/004"], "softshell", "dev"),
    sample("户外软壳脏了一点，必须整件洗吗？", "不一定。Mammut 建议尽可能局部清洁，只有真正需要时再进行完整洗涤。", ["mammut-softshell-001/tips/006"], "softshell", "test"),
    sample("Fleece 衣服怎么洗，哪些护理方式不能用？", "30°C/85°F 冷水、温和洗涤剂和常规程序；避免漂白、去渍剂、柔顺剂和干洗。", ["mammut-fleece-001/step-2-how-to-wash-fleece-and-functional-clothing/002"], "fleece", "dev"),
    sample("抓绒可以滚筒烘、熨烫或蒸汽处理吗？", "不可以。Mammut 建议挂晾，并避免滚筒烘、熨烫、蒸汽和干洗。", ["mammut-fleece-001/step-3-how-to-dry-fleece-and-functional-clothing/003"], "fleece", "test"),
    sample("夏天收纳抓绒，塑料袋可以吗？", "Mammut 建议在夏季将抓绒收纳在棉质袋中，而不是塑料袋中。", ["mammut-fleece-001/tips/004"], "storage", "test"),
    sample("Arc'teryx 的 DWR 应该在什么时候喷？", "DWR 只应施加在干净衣物上；Arc'teryx 建议每次洗后或衣物不再挂水时重新施加。", ["arcteryx-goretex-dwr-001/recare-protect/000"], "dwr", "dev"),
    sample("How can I keep down insulation lofted after washing?", "Dry the garment completely and thoroughly with two clean tennis balls or dryer balls to help redistribute the down and prevent clumping.", ["arcteryx-down-001/recare-wash-dry/001"], "down_drying", "dev"),
    sample("合成保温棉洗完怎么烘才不会伤材料？", "低温滚筒烘有助于恢复蓬松度；不要过热，因为部分合成面料和材料可能受损。", ["arcteryx-synthetic-001/recare-wash-dry/001"], "synthetic_insulation", "test"),
    sample("背包能直接扔进洗衣机吗？", "不能。Arc'teryx 建议只做表面清洗，用水或温和洗涤剂配软刷或海绵刷洗、充分冲净、避热风干。", ["arcteryx-other-001/recare-wash-dry/002"], "other_gear", "test"),
    sample("衣服沾到顽固污渍，Arc'teryx 的局部清洁建议是什么？", "先弄湿污渍，再用稀释的技术洗涤剂局部清洁；该指南建议 1 份 Nu Technical Detergent 配 3 份水。", ["arcteryx-stain-001/recare-stain-removal/000"], "stain_removal", "dev"),
    sample("为什么防水外套穿几次山里就感觉表层湿透了？", "随着 DWR 磨损，面布会出现 wetting-out；定期清洗和护理防水装备有助于维持表现。", ["rab-waterproof-001/how-to-wash-your-waterproof-jacket-and-pants/000"], "dwr", "dev"),
    sample("Rab 建议多久清洗和重新防泼水一次防水壳？", "建议每次出行后清洗，也应在外观变脏或 DWR 开始失效时清洗和重新防泼水。", ["rab-waterproof-001/why-do-you-need-to-wash-your-waterproof-gear/001"], "hardshell_washing", "test"),
    sample("野外没有洗衣机时，防水夹克怎么手洗？", "用凉水和温和洗涤剂手洗、充分冲净，并在避开直射阳光处留足时间干燥。", ["rab-waterproof-001/step-by-step-guide-to-washing-your-waterproof-jacket-and-pants/004"], "hardshell_washing", "dev"),
    sample("How should I machine-wash Rab waterproof pants?", "Check the care label, but most Rab waterproof jackets or pants can be machine washed around 30°C on a gentle cool setting, then low-spin and line dry.", ["rab-waterproof-001/step-by-step-guide-to-washing-your-waterproof-jacket-and-pants/003"], "hardshell_washing", "test"),
    sample("Rab 羽绒服应该用普通皂还是专用羽绒洗剂？", "可以使用普通非生物皂，但 Rab 为额外效果建议使用技术型羽绒专用洗涤剂；随后使用凉水、长而轻柔的程序。", ["rab-down-001/our-step-by-step-process-for-cleaning-your-down-jacket-or-vest/002"], "down_washing", "test"),
    sample("羽绒服洗后结团，是不是洗坏了？", "通常表示没有正确干透。可重新清洗；在滚筒烘前轻柔捏开隔仓内结团的羽绒，使其更均匀分布。", ["rab-down-001/why-is-my-down-jacket-clumping-after-washing/006"], "down_drying", "dev"),
    sample("Rab 羽绒服烘干时多久要拿出来拍一拍？", "Rab 建议中低温立即滚筒烘干，并每 20–30 分钟取出轻轻摇晃、拍打隔仓，帮助羽绒沿隔仓重新分布。", ["rab-down-001/our-step-by-step-process-for-cleaning-your-down-jacket-or-vest/003"], "down_drying", "dev"),
    sample("Can I air-dry a down jacket instead of tumble drying?", "Yes, but Rab recommends tumble drying to distribute down evenly. If air drying is the only option, shake it frequently to maximise loft.", ["rab-down-001/can-you-let-a-down-jacket-air-dry/008"], "down_drying", "test"),
    sample("Rab 羽绒服长期怎么收纳？", "为延长寿命，Rab 建议在阴凉干燥处不压缩地存放羽绒服。", ["rab-down-001/tips/005"], "storage", "test"),
    sample("我这件没有洗标的旧冲锋衣能不能直接按 30 度机洗？", "需要先确认衣物的洗标或具体材质与护理要求；当前知识库不能为未识别的衣物给出确定洗涤方案。", [], "missing_information", "dev"),
    sample("所有户外服装都能用同一种洗衣液吗？有没有通用选择？", "不能一概而论。不同衣物类型的官方护理建议对洗涤剂的要求并不完全相同，应按具体衣物的官方护理说明选择合适的洗涤剂。", ["arcteryx-synthetic-001/recare-wash-dry/000", "rab-waterproof-001/step-by-step-guide-to-washing-your-waterproof-jacket-and-pants/002"], "washing", "test"),
    sample("Can I temporarily repair minor punctures or tears in GORE-TEX outerwear in the field with a GORE-TEX Fabric Repair Kit?", "Yes. GORE-TEX says that minor punctures and tears can be temporarily repaired in the field with a GORE-TEX Fabric Repair Kit. Its special adhesive patches provide an instant but non-permanent repair until you can reach an authorized repair center.", ["goretex-faq-001/what-can-i-do-if-i-need-an-instant-repair/025"], "repair_maintenance", "test"),
    sample("我的羽绒服不知道是什么填充物，也没有洗标，能不能低温烘干？", "需要先确认填充物和洗标；当前知识库无法在这些关键条件缺失时给出确定的烘干建议。", [], "missing_information", "dev"),
    sample("冲锋衣沾了树胶或黏性污渍，Arc'teryx 建议怎么处理？", "先弄湿污渍，用稀释的技术洗涤剂局部清洁；对于树胶等黏性物质，可先用冰使其冻结，再用钝黄油刀刮除，随后用 1 份水和 1 份白醋的溶液浸泡。", ["arcteryx-stain-001/recare-stain-removal/000"], "stain_removal", "test"),
    sample("My jacket wets out quickly in rain. Does that mean the waterproof membrane is leaking?", "Not necessarily. Rab explains that worn DWR can make the face fabric wet out: water soaks into the surface instead of beading and rolling off. This evidence describes DWR wetting-out, but does not by itself establish membrane leakage.", ["rab-waterproof-001/how-to-wash-your-waterproof-jacket-and-pants/000"], "dwr", "dev"),
]


def main() -> None:
    chunks = {json.loads(line)["chunk_id"]: json.loads(line) for line in CHUNKS.read_text(encoding="utf-8").splitlines() if line.strip()}
    for record in CANDIDATES:
        missing = [chunk_id for chunk_id in record["gold_chunk_ids"] if chunk_id not in chunks]
        if missing:
            raise ValueError(f"Unknown gold chunk ids: {missing}")
    DATASET.parent.mkdir(parents=True, exist_ok=True)
    DATASET.write_text("".join(json.dumps(record, ensure_ascii=False) + "\n" for record in CANDIDATES), encoding="utf-8")
    with REVIEW.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["review_id", "question", "split", "category", "gt_answer", "gold_chunk_ids", "source_id", "source_title", "section_title", "gold_content_excerpt", "review_status", "review_note"])
        writer.writeheader()
        for index, record in enumerate(CANDIDATES, 1):
            evidence = [chunks[chunk_id] for chunk_id in record["gold_chunk_ids"]]
            writer.writerow({
                "review_id": f"candidate-{index:03d}", "question": record["question"], "split": record["split"],
                "category": record["category"], "gt_answer": record["gt_answer"],
                "gold_chunk_ids": " | ".join(record["gold_chunk_ids"]),
                "source_id": " | ".join(chunk["source_id"] for chunk in evidence),
                "source_title": " | ".join(chunk["source_title"] for chunk in evidence),
                "section_title": " | ".join(chunk["section_title"] for chunk in evidence),
                "gold_content_excerpt": " | ".join(chunk["content"][:500].replace("\n", " ") for chunk in evidence),
                "review_status": "pending", "review_note": "",
            })


if __name__ == "__main__":
    main()
