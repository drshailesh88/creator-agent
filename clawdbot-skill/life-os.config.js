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
  // SECURITY NOTE: Only content/research goes to AWS
  // Finance, health, HR stay LOCAL on your VPS (handled by Clawdbot directly)
  triggers: {
    // Content creation keywords → AWS
    content: [
      'write a', 'write me', 'create a', 'draft a', 'compose', 'blog post', 'article',
      'write content', 'copy for', 'script for', 'outline for', 'newsletter'
    ],

    // Research keywords → AWS
    research: [
      'research about', 'research on', 'analyze this topic', 'investigate',
      'pubmed', 'scientific papers', 'literature review', 'find studies'
    ],

    // Social media content keywords → AWS
    social: [
      'twitter thread', 'tweet about', 'linkedin post', 'social media post',
      'viral content', 'engagement post'
    ],

    // Graphics/infographic keywords → AWS
    graphics: [
      'infographic', 'create chart', 'visualize', 'diagram for'
    ],

    // =================================================================
    // EXCLUDED FROM AWS - These stay on your VPS with Firefly/Clawdbot:
    // - finance, expense, budget, loan, tax (→ Firefly III)
    // - health, medical, appointment (→ Local)
    // - hr, employee, payroll (→ Local)
    // - task, todo, reminder, calendar (→ Local)
    // =================================================================
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
