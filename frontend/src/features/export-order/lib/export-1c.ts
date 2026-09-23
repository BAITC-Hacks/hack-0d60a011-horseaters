import type { InventoryItem } from "@/entities/inventory";

export type ExportFormat = "xlsx" | "xml";

function download(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

function escapeXml(value: string): string {
  return value.replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&apos;");
}

export async function exportApprovedOrder(items: InventoryItem[], format: ExportFormat): Promise<number> {
  const approved = items.filter((item) => item.status === "approved" && (item.approvedQuantity ?? 0) > 0);
  if (approved.length === 0) throw new Error("Сначала утвердите позиции заказа.");
  const date = new Date().toISOString().slice(0, 10);

  if (format === "xml") {
    const lines = approved.map((item) => `<Товар><Артикул>${escapeXml(item.sku)}</Артикул><Наименование>${escapeXml(item.name)}</Наименование><Поставщик>${escapeXml(item.supplier)}</Поставщик><Количество>${item.approvedQuantity}</Количество><Единица>${escapeXml(item.unit)}</Единица><Цена>${item.unitCost}</Цена><Сумма>${(item.approvedQuantity ?? 0) * item.unitCost}</Сумма></Товар>`).join("");
    const xml = `<?xml version="1.0" encoding="UTF-8"?><ЗаказПоставщику><Организация>ТОО «Электрокомплект»</Организация><Дата>${date}</Дата><Валюта>KZT</Валюта><Товары>${lines}</Товары></ЗаказПоставщику>`;
    download(new Blob([xml], { type: "application/xml;charset=utf-8" }), `ekt-order-${date}.xml`);
    return approved.length;
  }

  const { default: ExcelJS } = await import("exceljs/dist/exceljs.min.js");
  const workbook = new ExcelJS.Workbook();
  workbook.creator = "ТОО Электрокомплект";
  workbook.created = new Date();
  const sheet = workbook.addWorksheet("Заказ поставщику");
  sheet.addRow(["ТОО «Электрокомплект» · Заказ поставщику"]);
  sheet.addRow([`Дата: ${date}`, "Валюта: KZT"]);
  sheet.addRow([]);
  sheet.addRow(["Артикул", "Номенклатура", "Поставщик", "Склад", "Количество", "Ед.", "Цена, ₸", "Сумма, ₸"]);
  sheet.getRow(4).font = { bold: true };
  sheet.getRow(4).fill = { type: "pattern", pattern: "solid", fgColor: { argb: "FFE8EEFF" } };
  for (const item of approved) sheet.addRow([item.sku, item.name, item.supplier, item.warehouse, item.approvedQuantity, item.unit, item.unitCost, (item.approvedQuantity ?? 0) * item.unitCost]);
  sheet.columns = [{ width: 24 }, { width: 52 }, { width: 24 }, { width: 16 }, { width: 16 }, { width: 10 }, { width: 18 }, { width: 20 }];
  sheet.getColumn(7).numFmt = "#,##0.00";
  sheet.getColumn(8).numFmt = "#,##0.00";
  const buffer = await workbook.xlsx.writeBuffer();
  download(new Blob([buffer as BlobPart], { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" }), `ekt-order-${date}.xlsx`);
  return approved.length;
}
