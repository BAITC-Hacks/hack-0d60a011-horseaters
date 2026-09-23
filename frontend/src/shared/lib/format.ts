const number = new Intl.NumberFormat("ru-RU");
const money = new Intl.NumberFormat("ru-RU", { maximumFractionDigits: 0 });

export const formatNumber = (value: number) => number.format(value);
export const formatMoney = (value: number) => `${money.format(value)} ₸`;
