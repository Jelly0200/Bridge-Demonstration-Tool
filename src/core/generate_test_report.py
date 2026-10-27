import statistics
from collections import defaultdict
from datetime import datetime

from PyQt6.QtCore import QMarginsF, QRectF, Qt
from PyQt6.QtGui import (
    QColor,
    QFont,
    QPageLayout,
    QPageSize,
    QPainter,
    QPdfWriter,
    QPen,
)

from src.ui.i18n import translate_text


def _format_score(value):
    if value is None:
        return "—"
    return f"{value:.2f}" if isinstance(value, float) else str(value)


def _build_report_sections(report_data, language):
    results = report_data["results"]
    tests = report_data["tests"]
    scores = [int(result["score"]) for result in results]
    unique_contestants = {
        result["student_id"]
        if result["student_id"] is not None
        else result["student_name"]
        for result in results
    }
    mean_score = float(statistics.mean(scores)) if scores else None
    median_score = float(statistics.median(scores)) if scores else None
    stddev = statistics.pstdev(scores) if scores else None
    stats_rows = [
        ("Administrator", report_data["administrator"]),
        ("Tests", len(tests)),
        ("Test attempts", len(results)),
        ("Contestants", len(unique_contestants)),
        ("Total score", sum(scores)),
        ("Average score", _format_score(mean_score)),
        ("Mean score", _format_score(mean_score)),
        ("Median score", _format_score(median_score)),
        ("Maximum score", _format_score(max(scores) if scores else None)),
        ("Minimum score", _format_score(min(scores) if scores else None)),
        ("Score standard deviation", _format_score(stddev)),
    ]

    problem_columns = []
    for test in tests:
        for index, problem in enumerate(test["problems"], start=1):
            problem_columns.append(
                (test["id"], int(problem.get("sequence", index)), test["name"])
            )
    problem_columns.sort(key=lambda item: (item[0], item[1]))
    ability_headers = [
        translate_text("Student ID", language),
        translate_text("Contestant", language),
        *(
            f"{test_name} — {translate_text('Problem ', language)}{sequence}"
            for _, sequence, test_name in problem_columns
        ),
    ]
    contestants = {}
    ability_scores = {}
    for result in results:
        student_key = (
            ("id", result["student_id"])
            if result["student_id"] is not None
            else ("name", result["student_name"])
        )
        contestants.setdefault(
            student_key,
            (result["student_id"], result["student_name"] or ""),
        )
        problem_results = result["contracts"]
        if not isinstance(problem_results, list):
            raise ValueError(f"Test result {result['id']} has invalid problem data.")
        for index, problem_result in enumerate(problem_results, start=1):
            if not isinstance(problem_result, dict):
                raise ValueError(
                    f"Test result {result['id']} has invalid problem data."
                )
            problem_number = int(problem_result.get("problem_number", index))
            ability_scores.setdefault(
                (student_key, result["test_id"], problem_number),
                int(problem_result["score"]),
            )
    ability_rows = []
    for student_key, (student_id, student_name) in sorted(
            contestants.items(),
            key=lambda item: (item[1][1].casefold(), item[1][0] or 0),
    ):
        ability_rows.append(
            [
                str(student_id or ""),
                student_name,
                *(
                    _format_score(
                        ability_scores.get((student_key, test_id, sequence))
                    )
                    for test_id, sequence, _test_name in problem_columns
                ),
            ]
        )

    candidate_scenarios = {}
    for test in tests:
        for problem in test["problems"]:
            for scenario_id in problem["scenario_ids"]:
                candidate_scenarios.setdefault(int(scenario_id), None)
    scenario_scores = defaultdict(list)
    for result in results:
        problem_results = result["contracts"]
        if not isinstance(problem_results, list):
            raise ValueError(f"Test result {result['id']} has invalid problem data.")
        for problem_result in problem_results:
            if not isinstance(problem_result, dict):
                raise ValueError(
                    f"Test result {result['id']} has invalid problem data."
                )
            scenario_id = int(problem_result["scenario_id"])
            candidate_scenarios.setdefault(scenario_id, None)
            scenario_scores[scenario_id].append(int(problem_result["score"]))
    scenario_rows = []
    for scenario_id in candidate_scenarios:
        scenario = report_data["scenarios"].get(scenario_id)
        if scenario is None:
            scenario_name = f"Scenario #{scenario_id}"
        else:
            scenario_name = " / ".join(
                part
                for part in (
                    scenario["case_name"],
                    scenario["board_name"],
                    scenario["name"],
                )
                if part
            )
        scenario_values = scenario_scores[scenario_id]
        mean = float(statistics.mean(scenario_values)) if scenario_values else None
        median = float(statistics.median(scenario_values)) if scenario_values else None
        scenario_rows.append(
            [
                scenario_name,
                _format_score(mean),
                _format_score(mean),
                _format_score(median),
                str(len(scenario_values)),
                _format_score(max(scenario_values) if scenario_values else None),
                _format_score(min(scenario_values) if scenario_values else None),
                _format_score(
                    statistics.pstdev(scenario_values) if scenario_values else None
                ),
            ]
        )
    scenario_rows.sort(key=lambda row: row[0].casefold())

    best_by_contestant = {}
    for result in results:
        student_key = (
            ("id", result["student_id"])
            if result["student_id"] is not None
            else ("name", result["student_name"])
        )
        current = best_by_contestant.get(student_key)
        if current is None or int(result["score"]) > int(current["score"]):
            best_by_contestant[student_key] = result
    top_three = sorted(
        best_by_contestant.values(),
        key=lambda result: (
            -int(result["score"]),
            (result["student_name"] or "").casefold(),
            result["submitted_at"] or "",
        ),
    )[:3]
    top_rows = [
        [
            str(rank),
            str(result["student_id"] or ""),
            result["student_name"] or "",
            result["test_name"],
            str(result["score"]),
        ]
        for rank, result in enumerate(top_three, start=1)
    ]
    return (
        stats_rows,
        ability_headers,
        ability_rows,
        scenario_rows,
        top_rows,
    )


_NAVY = QColor("#102a43")
_BLUE = QColor("#176b87")
_TEAL = QColor("#27a6a1")
_INK = QColor("#243b53")
_MUTED = QColor("#627d98")
_BORDER = QColor("#d9e2ec")
_PAPER = QColor("#f4f7fb")
_WHITE = QColor("#ffffff")


def _font(size: float, weight=QFont.Weight.Normal):
    font = QFont("Arial")
    font.setPointSizeF(size)
    font.setWeight(weight)
    return font


def _draw_text(
        painter,
        rect,
        text,
        size=11,
        color=_INK,
        weight=QFont.Weight.Normal,
        alignment=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
        padding=0,
):
    painter.setFont(_font(size, weight))
    painter.setPen(color)
    bounds = QRectF(rect).adjusted(padding, padding, -padding, -padding)
    painter.drawText(
        bounds,
        alignment | Qt.TextFlag.TextWordWrap,
        str(text),
    )


def _draw_footer(painter, page_rect, page_number, page_count, generated_at, language):
    x = page_rect.x()
    right = page_rect.right() + 1
    y = page_rect.bottom() - 25
    painter.setPen(QPen(_BORDER, 1))
    painter.drawLine(int(x), int(y), int(right), int(y))
    generated_label = translate_text("Generated", language)
    page_label = (
        f"Page {page_number} of {page_count}"
        if language == "en"
        else f"第 {page_number} 页，共 {page_count} 页"
    )
    _draw_text(
        painter,
        QRectF(x, y + 3, 500, 22),
        f"{generated_label}  ·  {generated_at}",
        size=8,
        color=_MUTED,
    )
    _draw_text(
        painter,
        QRectF(right - 180, y + 3, 180, 22),
        page_label,
        size=8,
        color=_MUTED,
        alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
    )


def _draw_cover_header(painter, page_rect, language, administrator, generated_at):
    width = page_rect.x() * 2 + page_rect.width()
    painter.fillRect(QRectF(0, 0, width, 164), _NAVY)
    painter.fillRect(QRectF(0, 157, width, 7), _TEAL)
    painter.setBrush(QColor("#234e70"))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawEllipse(QRectF(width - 295, -95, 360, 360))
    painter.setBrush(QColor("#176b87"))
    painter.drawEllipse(QRectF(width - 205, 12, 210, 210))

    left = page_rect.x()
    logo = QRectF(left, 34, 44, 44)
    painter.setBrush(_TEAL)
    painter.drawRoundedRect(logo, 10, 10)
    _draw_text(
        painter,
        logo,
        "BDT",
        size=11,
        color=_WHITE,
        weight=QFont.Weight.Bold,
        alignment=Qt.AlignmentFlag.AlignCenter,
    )
    title = translate_text("Test report", language)
    _draw_text(
        painter,
        QRectF(left + 59, 27, 530, 55),
        title,
        size=27,
        color=_WHITE,
        weight=QFont.Weight.Bold,
    )
    _draw_text(
        painter,
        QRectF(left + 1, 91, 720, 24),
        f"{translate_text('Administrator', language)}  ·  {administrator}",
        size=11,
        color=QColor("#d9eaf2"),
        weight=QFont.Weight.DemiBold,
    )
    _draw_text(
        painter,
        QRectF(left + 1, 119, 720, 20),
        f"{translate_text('Generated', language)}  ·  {generated_at}",
        size=9,
        color=QColor("#b8cbd9"),
    )


def _draw_page_heading(painter, page_rect, title, subtitle, language):
    width = page_rect.width()
    x = page_rect.x()
    painter.fillRect(QRectF(0, 0, x * 2 + width, 14), _NAVY)
    painter.fillRect(QRectF(0, 14, x * 2 + width, 4), _TEAL)
    _draw_text(
        painter,
        QRectF(x, page_rect.y() + 15, width, 34),
        translate_text("Bridge Demonstration Tool", language),
        size=9,
        color=_BLUE,
        weight=QFont.Weight.Bold,
    )
    _draw_text(
        painter,
        QRectF(x, page_rect.y() + 48, width, 39),
        title,
        size=20,
        color=_NAVY,
        weight=QFont.Weight.Bold,
    )
    if subtitle:
        _draw_text(
            painter,
            QRectF(x, page_rect.y() + 86, width, 24),
            subtitle,
            size=9,
            color=_MUTED,
        )


def _draw_section_title(painter, x, y, width, title, language):
    _draw_text(
        painter,
        QRectF(x, y, width - 8, 29),
        translate_text(title, language),
        size=13,
        color=_NAVY,
        weight=QFont.Weight.Bold,
    )
    painter.fillRect(QRectF(x, y + 31, 40, 3), _TEAL)


def _draw_metric_cards(painter, page_rect, stats, language):
    x = page_rect.x()
    gap = 12
    columns = 4
    card_width = (page_rect.width() - gap * (columns - 1)) / columns
    card_height = 82
    top = page_rect.y() + 134
    for index, (label, value) in enumerate(stats):
        row, column = divmod(index, columns)
        card = QRectF(
            x + column * (card_width + gap),
            top + row * (card_height + 10),
            card_width,
            card_height,
        )
        painter.setPen(QPen(_BORDER, 1))
        painter.setBrush(_WHITE)
        painter.drawRoundedRect(card, 8, 8)
        painter.fillRect(QRectF(card.left(), card.top() + 8, 4, card.height() - 16), _TEAL)
        _draw_text(
            painter,
            QRectF(card.left() + 13, card.top() + 8, card.width() - 23, 24),
            translate_text(label, language),
            size=8.5,
            color=_MUTED,
            weight=QFont.Weight.DemiBold,
        )
        _draw_text(
            painter,
            QRectF(card.left() + 13, card.top() + 32, card.width() - 23, 42),
            str(value),
            size=15 if len(str(value)) < 20 else 11,
            color=_NAVY,
            weight=QFont.Weight.Bold,
        )


def _draw_table(
        painter,
        x,
        y,
        widths,
        headers,
        rows,
        header_height,
        row_height,
        left_columns=(0,),
):
    header_rect = QRectF(x, y, sum(widths), header_height)
    painter.fillRect(header_rect, _NAVY)
    current_x = x
    for column, (width, label) in enumerate(zip(widths, headers)):
        cell = QRectF(current_x, y, width, header_height)
        painter.setPen(QPen(QColor("#49657f"), 0.8))
        painter.drawRect(cell)
        alignment = (
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
            if column in left_columns
            else Qt.AlignmentFlag.AlignCenter
        )
        _draw_text(
            painter,
            cell,
            label,
            size=8.5,
            color=_WHITE,
            weight=QFont.Weight.DemiBold,
            alignment=alignment,
            padding=5,
        )
        current_x += width

    for row_index, row in enumerate(rows):
        current_x = x
        row_y = y + header_height + row_index * row_height
        background = _WHITE if row_index % 2 == 0 else QColor("#edf3f8")
        for column, (width, value) in enumerate(zip(widths, row)):
            cell = QRectF(current_x, row_y, width, row_height)
            painter.fillRect(cell, background)
            painter.setPen(QPen(_BORDER, 0.7))
            painter.drawRect(cell)
            alignment = (
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
                if column in left_columns
                else Qt.AlignmentFlag.AlignCenter
            )
            _draw_text(
                painter,
                cell,
                value,
                size=8.5 if column < 2 else 8,
                color=_INK,
                alignment=alignment,
                padding=5,
            )
            current_x += width


def _draw_top_three(painter, page_rect, rows, language):
    x = page_rect.x()
    width = page_rect.width()
    _draw_section_title(
        painter,
        x,
        page_rect.y() + 428,
        width,
        "Top three contestants",
        language,
    )
    gap = 12
    card_width = (width - gap * 2) / 3
    top = page_rect.y() + 475
    card_height = 150
    medal_colors = (QColor("#d69e2e"), QColor("#8193a6"), QColor("#ba7551"))
    if not rows:
        card = QRectF(x, top, width, 82)
        painter.setPen(QPen(_BORDER, 1))
        painter.setBrush(_WHITE)
        painter.drawRoundedRect(card, 8, 8)
        _draw_text(
            painter,
            card,
            translate_text("No submissions yet.", language),
            size=11,
            color=_MUTED,
            alignment=Qt.AlignmentFlag.AlignCenter,
        )
        return

    for index, row in enumerate(rows):
        card = QRectF(
            x + index * (card_width + gap),
            top,
            card_width,
            card_height,
        )
        painter.setPen(QPen(_BORDER, 1))
        painter.setBrush(_WHITE)
        painter.drawRoundedRect(card, 8, 8)
        painter.setBrush(medal_colors[index])
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QRectF(card.left() + 14, card.top() + 14, 29, 29))
        _draw_text(
            painter,
            QRectF(card.left() + 14, card.top() + 14, 29, 29),
            row[0],
            size=10,
            color=_WHITE,
            weight=QFont.Weight.Bold,
            alignment=Qt.AlignmentFlag.AlignCenter,
        )
        _draw_text(
            painter,
            QRectF(card.left() + 53, card.top() + 12, card.width() - 65, 34),
            row[2],
            size=14,
            color=_NAVY,
            weight=QFont.Weight.Bold,
        )
        _draw_text(
            painter,
            QRectF(card.left() + 14, card.top() + 54, card.width() - 28, 25),
            row[3],
            size=9,
            color=_MUTED,
        )
        _draw_text(
            painter,
            QRectF(card.left() + 14, card.top() + 87, card.width() - 28, 42),
            f"{translate_text('Score', language)}  {row[4]}",
            size=17,
            color=medal_colors[index],
            weight=QFont.Weight.Bold,
        )


def _ability_pages(headers, rows):
    problem_count = max(0, len(headers) - 2)
    column_chunks = [
                        list(range(start, min(start + 6, problem_count)))
                        for start in range(0, problem_count, 6)
                    ] or [[]]
    row_chunks = [
                     rows[start: start + 17]
                     for start in range(0, len(rows), 17)
                 ] or [[]]
    return [
        (column_chunk, row_chunk)
        for row_chunk in row_chunks
        for column_chunk in column_chunks
    ]


def _scenario_pages(rows):
    return [
        rows[start: start + 8]
        for start in range(0, len(rows), 8)
    ] or [[]]


def _draw_ability_page(
        painter,
        page_rect,
        headers,
        rows,
        column_indexes,
        page_number,
        page_count,
        generated_at,
        language,
):
    problem_headers = [headers[index + 2] for index in column_indexes]
    if column_indexes:
        first_problem = column_indexes[0] + 1
        last_problem = column_indexes[-1] + 1
        subtitle = (
            f"Problems {first_problem}–{last_problem}"
            if language == "en"
            else f"题目 {first_problem}–{last_problem}"
        )
    else:
        subtitle = ""
    _draw_page_heading(
        painter,
        page_rect,
        translate_text("Contestant ability by problem", language),
        subtitle,
        language,
    )
    x = page_rect.x()
    widths = [72, 170]
    score_column_width = (page_rect.width() - sum(widths)) / max(
        len(problem_headers),
        1,
    )
    widths.extend([score_column_width] * len(problem_headers))
    selected_headers = headers[:2] + problem_headers
    selected_rows = [
        row[:2] + [row[index + 2] for index in column_indexes]
        for row in rows
    ]
    _draw_table(
        painter,
        x,
        page_rect.y() + 125,
        widths,
        selected_headers,
        selected_rows,
        header_height=62,
        row_height=27,
        left_columns=(0, 1),
    )
    _draw_footer(
        painter,
        page_rect,
        page_number,
        page_count,
        generated_at,
        language,
    )


def _draw_scenario_page(
        painter,
        page_rect,
        rows,
        page_number,
        page_count,
        generated_at,
        language,
):
    _draw_page_heading(
        painter,
        page_rect,
        translate_text("Scenario difficulty", language),
        "",
        language,
    )
    headers = [
        "Scenario",
        "Average score",
        "Mean score",
        "Median score",
        "Count",
        "Maximum score",
        "Minimum score",
        "Score standard deviation",
    ]
    headers = [translate_text(header, language) for header in headers]
    widths = [315, 100, 100, 100, 80, 100, 100, 121]
    _draw_table(
        painter,
        page_rect.x(),
        page_rect.y() + 122,
        widths,
        headers,
        rows,
        header_height=62,
        row_height=54,
    )
    _draw_footer(
        painter,
        page_rect,
        page_number,
        page_count,
        generated_at,
        language,
    )


def generate_pdf_report(report_data: dict, output_filename: str, language="en"):
    """Render a formatted, paginated test report to PDF."""
    stats, ability_headers, ability_rows, scenario_rows, top_rows = (
        _build_report_sections(report_data, language)
    )
    generated_at = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M")
    ability_pages = _ability_pages(ability_headers, ability_rows)
    scenario_pages = _scenario_pages(scenario_rows)
    page_count = 1 + len(ability_pages) + len(scenario_pages)

    writer = QPdfWriter(output_filename)
    writer.setResolution(96)
    writer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
    writer.setPageOrientation(QPageLayout.Orientation.Landscape)
    writer.setPageMargins(
        QMarginsF(14, 14, 14, 14),
        QPageLayout.Unit.Millimeter,
    )
    page_rect = writer.pageLayout().paintRectPixels(writer.resolution())
    full_rect = writer.pageLayout().fullRectPixels(writer.resolution())
    painter = QPainter()
    if not painter.begin(writer):
        raise OSError(f"Could not create PDF report at {output_filename}.")
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

    try:
        painter.fillRect(full_rect, _PAPER)
        _draw_cover_header(
            painter,
            page_rect,
            language,
            report_data["administrator"],
            generated_at,
        )
        _draw_metric_cards(painter, page_rect, stats, language)
        _draw_top_three(painter, page_rect, top_rows, language)
        _draw_footer(
            painter,
            page_rect,
            1,
            page_count,
            generated_at,
            language,
        )

        page_number = 1
        for column_indexes, rows in ability_pages:
            if not writer.newPage():
                raise OSError("Could not create a new page in the PDF report.")
            page_number += 1
            painter.fillRect(full_rect, _PAPER)
            _draw_ability_page(
                painter,
                page_rect,
                ability_headers,
                rows,
                column_indexes,
                page_number,
                page_count,
                generated_at,
                language,
            )

        for rows in scenario_pages:
            if not writer.newPage():
                raise OSError("Could not create a new page in the PDF report.")
            page_number += 1
            painter.fillRect(full_rect, _PAPER)
            _draw_scenario_page(
                painter,
                page_rect,
                rows,
                page_number,
                page_count,
                generated_at,
                language,
            )
    finally:
        painter.end()

    with open(output_filename, "rb") as pdf_file:
        if pdf_file.read(5) != b"%PDF-":
            raise OSError(f"Could not create a valid PDF report at {output_filename}.")
    return output_filename
