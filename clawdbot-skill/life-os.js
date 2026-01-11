/**
 * Life OS Integration Skill for Clawdbot
 *
 * Connects Clawdbot on VPS to the Life OS Master Router on AWS.
 * Routes messages to appropriate orchestrators based on intent.
 */

import config, { containsTrigger, getMatchedCategories, getAllTriggers } from './life-os.config.js';

/**
 * Sleep utility for retry delays
 * @param {number} ms - Milliseconds to sleep
 * @returns {Promise<void>}
 */
const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));

/**
 * Calculate retry delay with exponential backoff
 * @param {number} attempt - Current attempt number (0-indexed)
 * @returns {number} Delay in milliseconds
 */
function calculateRetryDelay(attempt) {
  const delay = config.retry.initialDelay * Math.pow(config.retry.backoffMultiplier, attempt);
  return Math.min(delay, config.retry.maxDelay);
}

/**
 * Log message based on configuration
 * @param {string} level - Log level
 * @param {string} message - Message to log
 * @param {object} [data] - Optional data to log
 */
function log(level, message, data = null) {
  if (!config.logging.enabled) return;

  const levels = ['debug', 'info', 'warn', 'error'];
  const configLevel = levels.indexOf(config.logging.level);
  const msgLevel = levels.indexOf(level);

  if (msgLevel >= configLevel) {
    const timestamp = new Date().toISOString();
    const prefix = `[${timestamp}] [LifeOS:${level.toUpperCase()}]`;

    if (data) {
      console[level](`${prefix} ${message}`, data);
    } else {
      console[level](`${prefix} ${message}`);
    }
  }
}

/**
 * Make authenticated request to Life OS API
 * @param {string} endpoint - API endpoint
 * @param {object} payload - Request payload
 * @param {object} options - Request options
 * @returns {Promise<object>} API response
 */
async function makeRequest(endpoint, payload, options = {}) {
  const url = `${config.api.url}${endpoint}`;
  const timeout = options.timeout || config.timeouts.default;

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeout);

  try {
    log('debug', `Making request to ${url}`, { payload });

    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${config.api.apiKey}`,
        'X-Source': 'clawdbot',
        'X-Request-Id': crypto.randomUUID(),
      },
      body: JSON.stringify(payload),
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      const errorBody = await response.text().catch(() => 'Unknown error');
      throw new Error(`API error (${response.status}): ${errorBody}`);
    }

    const data = await response.json();
    log('debug', 'Received response', { status: response.status });

    return data;
  } catch (error) {
    clearTimeout(timeoutId);

    if (error.name === 'AbortError') {
      throw new Error(`Request timeout after ${timeout}ms`);
    }

    throw error;
  }
}

/**
 * Make request with retry logic
 * @param {string} endpoint - API endpoint
 * @param {object} payload - Request payload
 * @param {object} options - Request options
 * @returns {Promise<object>} API response
 */
async function makeRequestWithRetry(endpoint, payload, options = {}) {
  let lastError;

  for (let attempt = 0; attempt < config.retry.maxAttempts; attempt++) {
    try {
      return await makeRequest(endpoint, payload, options);
    } catch (error) {
      lastError = error;

      // Check if error is retryable
      const statusMatch = error.message.match(/API error \((\d+)\)/);
      const status = statusMatch ? parseInt(statusMatch[1], 10) : null;

      const isRetryable =
        error.message.includes('timeout') ||
        error.message.includes('ECONNRESET') ||
        error.message.includes('ETIMEDOUT') ||
        (status && config.retry.retryableStatuses.includes(status));

      if (!isRetryable || attempt === config.retry.maxAttempts - 1) {
        throw error;
      }

      const delay = calculateRetryDelay(attempt);
      log('warn', `Request failed, retrying in ${delay}ms (attempt ${attempt + 1}/${config.retry.maxAttempts})`, {
        error: error.message,
      });

      await sleep(delay);
    }
  }

  throw lastError;
}

/**
 * Check Life OS health status
 * @returns {Promise<boolean>} True if Life OS is healthy
 */
async function checkHealth() {
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), config.timeouts.health);

    const response = await fetch(`${config.api.url}${config.api.healthEndpoint}`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${config.api.apiKey}`,
      },
      signal: controller.signal,
    });

    clearTimeout(timeoutId);
    return response.ok;
  } catch (error) {
    log('warn', 'Health check failed', { error: error.message });
    return false;
  }
}

/**
 * Format response for Clawdbot's personality
 * @param {string} response - Raw response from Life OS
 * @returns {string} Formatted response
 */
function formatResponse(response) {
  let formatted = response;

  // Add personality wrapper if configured
  if (config.response.personalityPrefix) {
    formatted = config.response.personalityPrefix + formatted;
  }

  if (config.response.personalitySuffix) {
    formatted = formatted + config.response.personalitySuffix;
  }

  // Truncate if too long
  if (formatted.length > config.response.maxLength) {
    formatted = formatted.substring(0, config.response.maxLength - config.response.truncationSuffix.length);
    formatted += config.response.truncationSuffix;
  }

  return formatted;
}

/**
 * Generate user-friendly error message
 * @param {Error} error - The error that occurred
 * @returns {string} User-friendly error message
 */
function getFriendlyErrorMessage(error) {
  const message = error.message.toLowerCase();

  if (message.includes('timeout')) {
    return "I'm having trouble reaching my brain right now - the request timed out. Could you try again in a moment?";
  }

  if (message.includes('api error (401)') || message.includes('api error (403)')) {
    return "I seem to have an authentication issue with my systems. Please let my human know to check the API credentials.";
  }

  if (message.includes('api error (429)')) {
    return "I've been thinking too hard and need a brief rest. Please try again in a few seconds.";
  }

  if (message.includes('api error (5')) {
    return "My backend systems are experiencing some issues. Please try again shortly.";
  }

  if (message.includes('econnrefused') || message.includes('enotfound')) {
    return "I can't seem to connect to my Life OS systems right now. Please check if everything is running.";
  }

  // Generic error
  return "Something went wrong while processing your request. Please try again or let my human know if this keeps happening.";
}

/**
 * Main handler function for the Life OS skill
 * @param {object} context - Message context from Clawdbot
 * @param {string} context.message - The user's message
 * @param {string} [context.userId] - User identifier
 * @param {string} [context.conversationId] - Conversation identifier
 * @param {object} [context.metadata] - Additional metadata
 * @returns {Promise<object>} Response object
 */
async function handler(context) {
  const { message, userId, conversationId, metadata = {} } = context;

  log('info', 'Processing message', {
    messageLength: message.length,
    userId,
    conversationId,
  });

  // Determine matched categories for routing hints
  const matchedCategories = getMatchedCategories(message);
  log('debug', 'Matched categories', { categories: matchedCategories });

  try {
    // Build request payload
    const payload = {
      message,
      context: {
        source: 'clawdbot',
        userId,
        conversationId,
        categories: matchedCategories,
        ...metadata,
      },
    };

    // Determine timeout based on request complexity
    const timeout = matchedCategories.includes('research') || matchedCategories.includes('content')
      ? config.timeouts.extended
      : config.timeouts.default;

    // Make request to Life OS Master Router
    const response = await makeRequestWithRetry(
      config.api.routerEndpoint,
      payload,
      { timeout }
    );

    // Extract and format the response
    const responseText = response.response || response.message || response.result || JSON.stringify(response);
    const formattedResponse = formatResponse(responseText);

    log('info', 'Successfully processed message', {
      orchestrator: response.orchestrator,
      responseLength: formattedResponse.length,
    });

    return {
      success: true,
      response: formattedResponse,
      metadata: {
        orchestrator: response.orchestrator,
        categories: matchedCategories,
        processingTime: response.processingTime,
      },
    };
  } catch (error) {
    log('error', 'Failed to process message', { error: error.message });

    return {
      success: false,
      response: getFriendlyErrorMessage(error),
      error: {
        message: error.message,
        categories: matchedCategories,
      },
    };
  }
}

/**
 * Life OS Skill Definition
 */
const lifeOsSkill = {
  // Skill identification
  name: 'life-os',
  description: 'Routes messages to Life OS orchestrators for content creation, research, finance, health, and more',
  version: '1.0.0',

  // Trigger configuration
  triggers: getAllTriggers(),

  // Check if a message should trigger this skill
  shouldTrigger: containsTrigger,

  // Get matched categories for a message
  getCategories: getMatchedCategories,

  // Main handler
  handler,

  // Health check
  checkHealth,

  // Configuration access
  config,
};

export default lifeOsSkill;
export { handler, checkHealth, containsTrigger, getMatchedCategories };
