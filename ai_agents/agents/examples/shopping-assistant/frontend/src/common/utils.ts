export const genUUID = (): string => {
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, function (c) {
    const r = (Math.random() * 16) | 0;
    const v = c === "x" ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
};

export const genRandomUserId = (): number => {
  return Math.floor(Math.random() * 100000) + 1;
};

export const genRandomChannel = (): string => {
  return `shopping_${Date.now()}`;
};
