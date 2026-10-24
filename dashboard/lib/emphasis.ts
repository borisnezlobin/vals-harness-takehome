export type TextRun = { text: string; strong: boolean };

export function splitEmphasis(text: string): TextRun[] {
  const runs: TextRun[] = [];
  const parts = text.split(/\*\*([\s\S]+?)\*\*/g);
  parts.forEach((part, index) => {
    if (part) runs.push({ text: part, strong: index % 2 === 1 });
  });
  return runs;
}
