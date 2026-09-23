import type { InventoryItem } from "../model";

export const demoInventory: InventoryItem[] = [
  { id: "1", sku: "FD-1042", name: "Филе куриное охлаждённое", category: "Мясо и птица", supplier: "Ферма Продукт", unit: "кг", stock: 18, minStock: 25, demand30: 120, leadDays: 4, packSize: 5, unitCost: 485 },
  { id: "2", sku: "FD-2108", name: "Молоко 3,2%, 1 л", category: "Молочная продукция", supplier: "Молочный дом", unit: "шт", stock: 42, minStock: 50, demand30: 210, leadDays: 3, packSize: 12, unitCost: 98 },
  { id: "3", sku: "FD-3084", name: "Рис длиннозёрный", category: "Бакалея", supplier: "АгроСнаб", unit: "кг", stock: 86, minStock: 40, demand30: 95, leadDays: 5, packSize: 10, unitCost: 142 },
  { id: "4", sku: "FD-1107", name: "Говядина бескостная", category: "Мясо и птица", supplier: "Ферма Продукт", unit: "кг", stock: 12, minStock: 20, demand30: 75, leadDays: 6, packSize: 5, unitCost: 890 },
  { id: "5", sku: "FD-4021", name: "Масло подсолнечное, 1 л", category: "Бакалея", supplier: "АгроСнаб", unit: "шт", stock: 64, minStock: 45, demand30: 150, leadDays: 4, packSize: 12, unitCost: 168 },
  { id: "6", sku: "FD-5013", name: "Помидоры свежие", category: "Овощи и фрукты", supplier: "Зелёная линия", unit: "кг", stock: 28, minStock: 30, demand30: 90, leadDays: 2, packSize: 5, unitCost: 235 },
  { id: "7", sku: "FD-2115", name: "Сыр гауда 45%", category: "Молочная продукция", supplier: "Молочный дом", unit: "кг", stock: 34, minStock: 18, demand30: 60, leadDays: 5, packSize: 2, unitCost: 720 },
  { id: "8", sku: "FD-5029", name: "Огурцы свежие", category: "Овощи и фрукты", supplier: "Зелёная линия", unit: "кг", stock: 15, minStock: 25, demand30: 80, leadDays: 2, packSize: 5, unitCost: 190 },
  { id: "9", sku: "FD-3090", name: "Макароны из твёрдых сортов", category: "Бакалея", supplier: "АгроСнаб", unit: "кг", stock: 105, minStock: 35, demand30: 100, leadDays: 5, packSize: 10, unitCost: 128 },
  { id: "10", sku: "FD-2122", name: "Сливки 20%, 1 л", category: "Молочная продукция", supplier: "Молочный дом", unit: "шт", stock: 23, minStock: 20, demand30: 75, leadDays: 3, packSize: 6, unitCost: 245 },
  { id: "11", sku: "FD-5035", name: "Картофель мытый", category: "Овощи и фрукты", supplier: "Зелёная линия", unit: "кг", stock: 140, minStock: 60, demand30: 210, leadDays: 3, packSize: 10, unitCost: 82 },
  { id: "12", sku: "FD-1121", name: "Индейка филе", category: "Мясо и птица", supplier: "Ферма Продукт", unit: "кг", stock: 37, minStock: 25, demand30: 70, leadDays: 4, packSize: 5, unitCost: 645 },
];
