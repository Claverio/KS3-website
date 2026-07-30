(function () {
    "use strict";

    var currency = new Intl.NumberFormat("id-ID", {
        style: "currency",
        currency: "IDR",
        maximumFractionDigits: 0
    });

    function money(value) {
        return currency.format(Number(value || 0));
    }

    function create(tag, className, textValue) {
        var element = document.createElement(tag);
        if (className) element.className = className;
        if (textValue !== undefined) element.textContent = textValue;
        return element;
    }

    function svgElement(tag, attributes) {
        var element = document.createElementNS("http://www.w3.org/2000/svg", tag);
        Object.keys(attributes || {}).forEach(function (key) {
            element.setAttribute(key, attributes[key]);
        });
        return element;
    }

    function compactMoney(value) {
        var number = Number(value || 0);
        if (number >= 1000000000) return "Rp" + (number / 1000000000).toFixed(number >= 10000000000 ? 0 : 1) + " M";
        if (number >= 1000000) return "Rp" + (number / 1000000).toFixed(number >= 10000000 ? 0 : 1) + " jt";
        if (number >= 1000) return "Rp" + (number / 1000).toFixed(0) + " rb";
        return "Rp" + number.toFixed(0);
    }

    function renderSummary(root, result, kind) {
        var summary = root.querySelector("[data-simulator-summary]");
        summary.replaceChildren();
        var items;
        if (kind === "savings") {
            items = [
                ["Saldo saat jatuh tempo", result.summary.maturity_balance],
                ["Total setoran", result.summary.total_contributions],
                ["Bunga bersih", result.summary.net_interest],
                ["Pajak & biaya", Number(result.summary.total_tax) + Number(result.summary.total_fees)]
            ];
        } else {
            var installment = Math.round(Number(result.summary.installment_min)) === Math.round(Number(result.summary.installment_max))
                ? money(result.summary.installment_max)
                : money(result.summary.installment_min) + " – " + money(result.summary.installment_max);
            items = [
                ["Estimasi angsuran", installment, true],
                ["Total pembayaran", result.summary.total_scheduled_payment],
                ["Total bunga", result.summary.total_interest],
                ["Dana bersih diterima", result.summary.net_disbursed]
            ];
        }
        items.forEach(function (item) {
            var card = create("div", "ks3-simulator__summary-card");
            card.appendChild(create("span", "ks3-simulator__summary-label", item[0]));
            card.appendChild(create("strong", "ks3-simulator__summary-value", item[2] ? item[1] : money(item[1])));
            summary.appendChild(card);
        });
    }

    function renderRules(root, result) {
        var note = root.querySelector("[data-simulator-rules]");
        if (!note) return;
        var rates = (result.applied_rules.rates || []).map(function (rule) {
            return rule.label + " (" + Number(rule.annual_rate).toLocaleString("id-ID") + "% p.a.)";
        });
        var charges = (result.applied_rules.charges || []).map(function (rule) { return rule.label; });
        var parts = [];
        if (rates.length) parts.push("Bunga: " + rates.join(", "));
        if (charges.length) parts.push("Biaya/pajak: " + charges.join(", "));
        note.textContent = parts.join(" • ");
        note.hidden = parts.length === 0;
    }

    function renderTable(root, result, kind) {
        var head = root.querySelector("[data-breakdown-head]");
        var body = root.querySelector("[data-breakdown-body]");
        if (!head || !body) return;
        var columns = kind === "savings" ? [
            ["label", "Periode", false],
            ["opening_balance", "Saldo awal", true],
            ["inflow", "Setoran", true],
            ["interest", "Bunga", true],
            ["fees", "Biaya", true],
            ["tax", "Pajak", true],
            ["closing_balance", "Saldo akhir", true]
        ] : [
            ["label", "Periode", false],
            ["opening_balance", "Sisa awal", true],
            ["principal", "Pokok", true],
            ["interest", "Bunga", true],
            ["fees", "Biaya", true],
            ["tax", "Pajak", true],
            ["payment", "Total bayar", true],
            ["closing_balance", "Sisa pokok", true]
        ];
        var headerRow = create("tr");
        columns.forEach(function (column) { headerRow.appendChild(create("th", "", column[1])); });
        head.replaceChildren(headerRow);
        body.replaceChildren();
        result.breakdown.forEach(function (row) {
            var tableRow = create("tr");
            columns.forEach(function (column) {
                tableRow.appendChild(create("td", "", column[2] ? money(row[column[0]]) : row[column[0]]));
            });
            body.appendChild(tableRow);
        });
        root.querySelector("[data-breakdown-count]").textContent = result.metadata.breakdown_rows + " periode tampilan";
        root.querySelector("[data-breakdown-title]").textContent = result.metadata.breakdown_interval_months === 1
            ? "Breakdown bulanan"
            : "Breakdown per " + result.metadata.breakdown_interval_months + " bulan";
    }

    function renderChart(root, result, kind) {
        var chart = root.querySelector("[data-simulator-chart]");
        if (!chart || !result.chart.length) return;
        var svg = chart.querySelector("svg");
        var tooltip = chart.querySelector("[data-chart-tooltip]");
        var legend = root.querySelector("[data-chart-legend]");
        svg.replaceChildren();
        legend.replaceChildren();

        var colors = { total: "#005daa", principal: "#159a80", interest: "#f3a712" };
        var series = kind === "savings" ? [
            { key: "closing_balance", name: "Total saldo", color: colors.total },
            { key: "cumulative_principal", name: "Pokok/setoran", color: colors.principal },
            { key: "cumulative_interest", name: "Bunga bruto", color: colors.interest }
        ] : [
            { key: "cumulative_total", name: "Total pembayaran", color: colors.total },
            { key: "cumulative_principal", name: "Pokok terbayar", color: colors.principal },
            { key: "cumulative_interest", name: "Bunga", color: colors.interest }
        ];
        series.forEach(function (item) {
            var legendItem = create("span", "ks3-simulator__legend-item");
            var dot = create("span", "ks3-simulator__legend-dot");
            dot.style.background = item.color;
            legendItem.appendChild(dot);
            legendItem.appendChild(document.createTextNode(item.name));
            legend.appendChild(legendItem);
        });

        var width = 900, height = 350;
        var margin = { top: 22, right: 28, bottom: 48, left: 78 };
        var plotWidth = width - margin.left - margin.right;
        var plotHeight = height - margin.top - margin.bottom;
        var maximum = Math.max.apply(null, result.chart.reduce(function (values, row) {
            return values.concat(series.map(function (item) { return Number(row[item.key] || 0); }));
        }, [1]));
        maximum *= 1.08;
        var x = function (index) {
            return margin.left + (result.chart.length === 1 ? plotWidth / 2 : index * plotWidth / (result.chart.length - 1));
        };
        var y = function (value) { return margin.top + plotHeight - (Number(value) / maximum) * plotHeight; };

        for (var gridIndex = 0; gridIndex <= 4; gridIndex += 1) {
            var gridY = margin.top + gridIndex * plotHeight / 4;
            svg.appendChild(svgElement("line", { x1: margin.left, x2: width - margin.right, y1: gridY, y2: gridY, class: "ks3-chart-grid" }));
            var label = svgElement("text", { x: margin.left - 12, y: gridY + 4, "text-anchor": "end", class: "ks3-chart-axis-label" });
            label.textContent = compactMoney(maximum * (4 - gridIndex) / 4);
            svg.appendChild(label);
        }

        var tickIndexes = [0, Math.floor((result.chart.length - 1) / 2), result.chart.length - 1].filter(function (value, index, values) {
            return values.indexOf(value) === index;
        });
        tickIndexes.forEach(function (index) {
            var label = svgElement("text", { x: x(index), y: height - 16, "text-anchor": "middle", class: "ks3-chart-axis-label" });
            label.textContent = "Bulan " + result.chart[index].period_end;
            svg.appendChild(label);
        });

        function pathFor(key) {
            return result.chart.map(function (row, index) {
                return (index === 0 ? "M" : "L") + x(index).toFixed(2) + " " + y(row[key]).toFixed(2);
            }).join(" ");
        }

        var totalPath = pathFor(series[0].key);
        var areaPath = totalPath + " L" + x(result.chart.length - 1) + " " + (margin.top + plotHeight) +
            " L" + x(0) + " " + (margin.top + plotHeight) + " Z";
        svg.appendChild(svgElement("path", { d: areaPath, fill: colors.total, "fill-opacity": ".1" }));
        series.forEach(function (item) {
            svg.appendChild(svgElement("path", { d: pathFor(item.key), stroke: item.color, class: "ks3-chart-line" }));
        });

        var focusLine = svgElement("line", { y1: margin.top, y2: margin.top + plotHeight, class: "ks3-chart-focus-line", visibility: "hidden" });
        svg.appendChild(focusLine);
        var focusDots = series.map(function (item) {
            var dot = svgElement("circle", { r: 5, fill: item.color, class: "ks3-chart-focus-dot", visibility: "hidden" });
            svg.appendChild(dot);
            return dot;
        });
        var hit = svgElement("rect", { x: margin.left, y: margin.top, width: plotWidth, height: plotHeight, class: "ks3-chart-hit" });
        svg.appendChild(hit);

        hit.addEventListener("mousemove", function (event) {
            var rect = svg.getBoundingClientRect();
            var relativeX = ((event.clientX - rect.left) / rect.width) * width;
            var index = Math.max(0, Math.min(result.chart.length - 1, Math.round((relativeX - margin.left) / plotWidth * (result.chart.length - 1))));
            var row = result.chart[index];
            var pointX = x(index);
            focusLine.setAttribute("x1", pointX);
            focusLine.setAttribute("x2", pointX);
            focusLine.setAttribute("visibility", "visible");
            focusDots.forEach(function (dot, seriesIndex) {
                dot.setAttribute("cx", pointX);
                dot.setAttribute("cy", y(row[series[seriesIndex].key]));
                dot.setAttribute("visibility", "visible");
            });
            tooltip.replaceChildren(create("strong", "", row.label));
            series.forEach(function (item) {
                tooltip.appendChild(create("span", "", item.name + ": " + money(row[item.key])));
            });
            tooltip.hidden = false;
            var chartRect = chart.getBoundingClientRect();
            var tooltipHalfWidth = tooltip.offsetWidth / 2;
            var tooltipHeight = tooltip.offsetHeight;
            var pointClientX = rect.left + (pointX / width * rect.width);
            var pointClientY = rect.top + (y(row[series[0].key]) / height * rect.height);
            var tooltipX = pointClientX - chartRect.left;
            var tooltipY = pointClientY - chartRect.top;
            tooltipX = Math.max(tooltipHalfWidth + 8, Math.min(chartRect.width - tooltipHalfWidth - 8, tooltipX));
            tooltipY = Math.max(tooltipHeight + 18, tooltipY);
            tooltip.style.left = tooltipX + "px";
            tooltip.style.top = tooltipY + "px";
        });
        function hideTooltip() {
            focusLine.setAttribute("visibility", "hidden");
            focusDots.forEach(function (dot) { dot.setAttribute("visibility", "hidden"); });
            tooltip.hidden = true;
        }
        hit.addEventListener("mouseleave", hideTooltip);
        hit.addEventListener("pointerleave", hideTooltip);
        chart.onmouseleave = hideTooltip;
        chart.onpointerleave = hideTooltip;
        if (chart._simulatorTooltipOutsideHandler) {
            document.removeEventListener("mousemove", chart._simulatorTooltipOutsideHandler);
            document.removeEventListener("pointermove", chart._simulatorTooltipOutsideHandler);
        }
        chart._simulatorTooltipOutsideHandler = function (event) {
            if (!chart.contains(event.target)) hideTooltip();
        };
        document.addEventListener("mousemove", chart._simulatorTooltipOutsideHandler);
        document.addEventListener("pointermove", chart._simulatorTooltipOutsideHandler);
    }

    function showError(root, errors) {
        var box = root.querySelector("[data-simulator-error]");
        var messages = [];
        Object.keys(errors || {}).forEach(function (field) {
            (errors[field] || []).forEach(function (message) { messages.push(message); });
            var input = root.querySelector("[name='" + field + "']");
            if (input) input.setAttribute("aria-invalid", "true");
        });
        box.textContent = messages.join(" ") || "Simulasi belum dapat dihitung. Silakan periksa kembali input Anda.";
        box.hidden = false;
    }

    function initialize(root) {
        var configElement = root.querySelector("#product-simulation-config");
        if (!configElement) return;
        var config = JSON.parse(configElement.textContent);
        var form = root.querySelector("[data-simulator-form]");
        var submit = root.querySelector("[data-simulator-submit]");
        var results = root.querySelector("[data-simulator-results]");
        var error = root.querySelector("[data-simulator-error]");

        form.addEventListener("submit", function (event) {
            event.preventDefault();
            error.hidden = true;
            form.querySelectorAll("[aria-invalid]").forEach(function (input) { input.removeAttribute("aria-invalid"); });
            if (!form.checkValidity()) {
                form.reportValidity();
                return;
            }
            var url = new URL(root.dataset.endpoint, window.location.origin);
            new FormData(form).forEach(function (value, key) { url.searchParams.set(key, value); });
            submit.disabled = true;
            submit.classList.add("is-loading");
            fetch(url.toString(), { headers: { "Accept": "application/json" }, credentials: "same-origin" })
                .then(function (response) {
                    return response.json().then(function (body) {
                        if (!response.ok) throw body;
                        return body;
                    });
                })
                .then(function (result) {
                    renderSummary(root, result, config.product_kind);
                    renderChart(root, result, config.product_kind);
                    renderTable(root, result, config.product_kind);
                    renderRules(root, result);
                    root.querySelector("[data-simulator-method]").textContent = result.metadata.strategy_label;
                    results.hidden = false;
                })
                .catch(function (response) {
                    results.hidden = true;
                    showError(root, response && response.errors ? response.errors : { request: [response.error || "Terjadi gangguan saat menghitung simulasi."] });
                })
                .finally(function () {
                    submit.disabled = false;
                    submit.classList.remove("is-loading");
                });
        });

        form.requestSubmit();
    }

    document.addEventListener("DOMContentLoaded", function () {
        document.querySelectorAll("[data-simulator]").forEach(initialize);
    });
}());
