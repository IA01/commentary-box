export function isValidUrl(url: string) {
  try {
    new URL(url)
    return true
  } catch {
    return false
  }
}

export const commentators = [
  {
    id: "ravi",
    name: "Ravi's Roast",
    description: "Playful criticism with signature phrases",
    emoji: "🔥",
    color: "bg-red-500",
  },
  {
    id: "harsha",
    name: "Bhogle's Balance",
    description: "Balanced and analytical insights",
    emoji: "❄️",
    color: "bg-blue-500",
  },
  {
    id: "jatin",
    name: "Jatin's Jubilation",
    description: "Ultra-positive and high-energy takes",
    emoji: "⚡",
    color: "bg-yellow-500",
  },
] as const 