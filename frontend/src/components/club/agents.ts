// English is the display language; `zh` keeps each persona's original Chinese name as a secondary label.
export const AGENT_OPTIONS = [
  { id: "laowang",  name: "Wang",         zh: "老王",     difficulty: "easy",   style: "Ultra-tight" },
  { id: "dushen",   name: "Ace",          zh: "赌神",     difficulty: "hard",   style: "Hyper-aggressive" },
  { id: "jiaoshou", name: "Prof",         zh: "教授",     difficulty: "medium", style: "Math-driven" },
  { id: "xiaoli",   name: "Li",           zh: "小李",     difficulty: "easy",   style: "Erratic" },
  { id: "pukelian", name: "Bluff",        zh: "扑克脸",   difficulty: "medium", style: "Deceptive" },
  { id: "meimei",   name: "Meimei",       zh: "美美",     difficulty: "easy",   style: "Social" },
  { id: "luobo",    name: "Radish",       zh: "萝卜头",   difficulty: "easy",   style: "Position-aware" },
  { id: "laohu",    name: "Tiger",        zh: "老虎",     difficulty: "medium", style: "Tight-aggressive" },
  { id: "xiaoming", name: "Ming",         zh: "小明",     difficulty: "easy",   style: "Calling station" },
  { id: "nvwang",   name: "Queen",        zh: "女王",     difficulty: "hard",   style: "Hand reader" },
  { id: "guanjun",  name: "Champ",        zh: "世界冠军", difficulty: "hard",   style: "All-rounder" },
  { id: "wangzhe",  name: "Solver",       zh: "网络之王", difficulty: "hard",   style: "GTO machine" },
  { id: "kuangmo",  name: "Maniac",       zh: "狂魔",     difficulty: "medium", style: "Super-aggressive" },
  { id: "lengxue",  name: "Ice",          zh: "冷血",     difficulty: "hard",   style: "Exploitative" },
  { id: "laoqian",  name: "Sharp",        zh: "千王",     difficulty: "medium", style: "Mind games" },
];

const byPlayerId = new Map(AGENT_OPTIONS.map(agent => [`agent_${agent.id}`, agent]));

// Server player ids are `agent_<persona id>`; anything unknown (the human, custom personas) keeps its own name.
export const agentInfo = (playerId: string) => byPlayerId.get(playerId);
export const displayName = (playerId: string, fallback: string) => agentInfo(playerId)?.name || fallback;
