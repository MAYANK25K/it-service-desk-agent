const ORDER = ["Today", "Yesterday", "Earlier"];

function startOfDay(date) {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate());
}

function timeOf(thread) {
  return Date.parse(thread.updated_at) || 0;
}

export function groupThreads(threads, now = new Date()) {
  const today = startOfDay(now);
  const yesterday = new Date(today);
  yesterday.setDate(today.getDate() - 1);

  const groups = { Today: [], Yesterday: [], Earlier: [] };
  const newestFirst = [...threads].sort((a, b) => timeOf(b) - timeOf(a));

  for (const thread of newestFirst) {
    const when = new Date(thread.updated_at);
    if (Number.isNaN(when.getTime())) {
      groups.Earlier.push(thread);
    } else if (startOfDay(when) >= today) {
      groups.Today.push(thread);
    } else if (startOfDay(when) >= yesterday) {
      groups.Yesterday.push(thread);
    } else {
      groups.Earlier.push(thread);
    }
  }

  return ORDER.filter((label) => groups[label].length > 0).map((label) => ({
    label,
    threads: groups[label],
  }));
}