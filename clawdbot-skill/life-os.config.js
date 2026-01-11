/**
 * Life OS Integration Configuration
 *
 * Configuration for connecting Clawdbot to the Life OS Master Router on AWS
 */

export const config = {
  // API Configuration
  api: {
    // Life OS Master Router URL (from environment)
    url: process.env.LIFE_OS_API_URL || 'http://localhost:8000',

    // API Key for authentication
    apiKey: process.env.LIFE_OS_API_KEY || '',

    // Router endpoint
    routerEndpoint: '/api/v1/route',

    // Health check endpoint
    healthEndpoint: '/health',
  },

  // Timeout Configuration
  timeouts: {
    // Default request timeout (30 seconds)
    default: 30000,

    // Extended timeout for complex operations (2 minutes)
    extended: 120000,

    // Health check timeout (5 seconds)
    health: 5000,
  },

  // Retry Configuration
  retry: {
    // Maximum number of retry attempts
    maxAttempts: 3,

    // Initial delay between retries (milliseconds)
    initialDelay: 1000,

    // Backoff multiplier for each retry
    backoffMultiplier: 2,

    // Maximum delay between retries
    maxDelay: 10000,

    // HTTP status codes that trigger a retry
    retryableStatuses: [408, 429, 500, 502, 503, 504],
  },

  // Trigger Keywords - messages containing these route to Life OS
  triggers: {
    // Content creation keywords
    content: [
      'write', 'create', 'draft', 'compose', 'blog', 'article',
      'post', 'content', 'copy', 'script', 'outline'
    ],

    // Research keywords
    research: [
      'research', 'analyze', 'investigate', 'study', 'find',
      'search', 'lookup', 'pubmed', 'papers', 'literature'
    ],

    // Social media keywords
    social: [
      'twitter', 'tweet', 'x post', 'linkedin', 'social',
      'thread', 'viral', 'engagement'
    ],

    // Finance keywords
    finance: [
      'finance', 'loan', 'mortgage', 'investment', 'budget',
      'expense', 'income', 'tax', 'savings', 'portfolio'
    ],

    // HR keywords
    hr: [
      'hr', 'human resources', 'employee', 'hiring', 'recruit',
      'onboard', 'payroll', 'benefits', 'performance'
    ],

    // Health keywords
    health: [
      'health', 'medical', 'doctor', 'appointment', 'medication',
      'wellness', 'fitness', 'nutrition', 'symptom'
    ],

    // Task management keywords
    tasks: [
      'task', 'todo', 'schedule', 'calendar', 'reminder',
      'deadline', 'project', 'milestone'
    ],
  },

  // Response formatting
  response: {
    // Maximum response length (characters)
    maxLength: 4000,

    // Truncation suffix when response is too long
    truncationSuffix: '\n\n... (response truncated)',

    // Clawdbot personality wrapper
    personalityPrefix: '',
    personalitySuffix: '',
  },

  // Logging configuration
  logging: {
    // Enable request/response logging
    enabled: process.env.NODE_ENV !== 'production',

    // Log level: 'debug', 'info', 'warn', 'error'
    level: process.env.LOG_LEVEL || 'info',
  },
};

/**
 * Get all trigger keywords as a flat array
 * @returns {string[]} Array of all trigger keywords
 */
export function getAllTriggers() {
  return Object.values(config.triggers).flat();
}

/**
 * Check if a message contains any trigger keywords
 * @param {string} message - The message to check
 * @returns {boolean} True if message contains trigger keywords
 */
export function containsTrigger(message) {
  const lowerMessage = message.toLowerCase();
  const allTriggers = getAllTriggers();
  return allTriggers.some(trigger => lowerMessage.includes(trigger.toLowerCase()));
}

/**
 * Get the category of triggers matched
 * @param {string} message - The message to check
 * @returns {string[]} Array of matched trigger categories
 */
export function getMatchedCategories(message) {
  const lowerMessage = message.toLowerCase();
  const matched = [];

  for (const [category, keywords] of Object.entries(config.triggers)) {
    if (keywords.some(keyword => lowerMessage.includes(keyword.toLowerCase()))) {
      matched.push(category);
    }
  }

  return matched;
}

export default config;
