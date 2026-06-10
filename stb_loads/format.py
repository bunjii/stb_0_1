from stb_loads.seismic import SeismicDistributionResult


def render_seismic_markdown(result: SeismicDistributionResult) -> str:
    lines = []
    lines.append("## 地震力 Ai 分布")
    lines.append("")
    lines.append("| 項目 | 値 |")
    lines.append("| --- | --- |")
    lines.append("| Ci (入力) | {0:.4f} |".format(result.ci_input))
    lines.append("| Rt | {0:.4f} |".format(result.rt))
    lines.append("| Ci (有効 = Ci×Rt) | {0:.4f} |".format(result.ci))
    lines.append("| base_level | {0} |".format(result.base_level))
    lines.append("| base_mass_policy | {0} |".format(result.base_mass_policy))
    lines.append("| Wi LCs (TYPE 1+3) | {0} |".format(
        ", ".join(str(lc) for lc in result.weight_result.weight_load_cases) or "-"
    ))
    lines.append("| ΣWi kN (質量レベル) | {0:.3f} |".format(result.total_weight_kN))
    lines.append("| V=Ci*ΣWi kN | {0:.3f} |".format(result.base_shear_kN))
    lines.append("| ΣQi kN | {0:.3f} |".format(sum(s.qi_kN for s in result.stories)))
    lines.append("| ΣFi kN | {0:.3f} |".format(sum(s.fi_kN for s in result.stories)))
    lines.append("")

    lines.append("### 質量レベル重量・Ai・Qi・Fi")
    lines.append("")
    lines.append("| 階 | Wi kN | hi m | βi | Ai | Qi kN | Fi kN | DLOD |")
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |")
    for s in result.stories:
        lines.append(
            "| {0} | {1:.3f} | {2:.3f} | {3:.4f} | {4:.4f} | {5:.3f} | {6:.3f} | {7} |".format(
                s.story_name,
                s.weight_kN,
                s.mass_height_m,
                s.beta,
                s.ai,
                s.qi_kN,
                s.fi_kN,
                "yes" if s.output_dlod else "no",
            )
        )
    lines.append("")

    if result.diaphragm_loads:
        lines.append("### ダイアフラム DLOD (TYPE=0 AREA, Fi ベース)")
        lines.append("")
        lines.append("| DIAP | 階 | LC | 方向 | 面積 m2 | Fi kN | kN/m2 |")
        lines.append("| --- | --- | ---: | --- | ---: | ---: | ---: |")
        for d in result.diaphragm_loads:
            lines.append(
                "| {0} | {1} | {2} | {3}{4} | {5:.3f} | {6:.3f} | {7:.4f} |".format(
                    d.diaphragm_id,
                    d.story_name,
                    d.load_case,
                    d.axis.upper(),
                    "+" if d.sign >= 0 else "-",
                    d.area_m2,
                    d.fi_kN,
                    d.pressure_kN_m2,
                )
            )
        lines.append("")

    if result.warnings:
        lines.append("### 警告")
        lines.append("")
        for w in result.warnings:
            lines.append("- " + w)
        lines.append("")

    return "\n".join(lines)
