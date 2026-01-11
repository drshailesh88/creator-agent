# Life OS Integration Skill for Clawdbot

This skill connects Clawdbot (running on VPS) to the Life OS Master Router (running on AWS), enabling intelligent routing of user requests to specialized orchestrators.

## Overview

The Life OS skill intercepts messages containing specific trigger keywords and routes them to the appropriate Life OS orchestrator for processing. This enables Clawdbot to leverage the full power of the Life OS system including:

- **Content Creation**: Blog posts, articles, social media content
- **Research**: Literature reviews, PubMed searches, web research
- **Finance**: Loan management, budgeting, investment tracking
- **Health**: Medical appointments, wellness tracking
- **HR**: Employee management, hiring workflows
- **Task Management**: Scheduling, reminders, project tracking

## Installation

### 1. Copy Skill Files

Copy the skill files to your Clawdbot skills directory:

```bash
cp -r clawdbot-skill/* /path/to/clawdbot/skills/life-os/
```

### 2. Set Environment Variables

Add the following environment variables to your Clawdbot configuration:

```bash
# Life OS API URL (AWS endpoint)
export LIFE_OS_API_URL="https://your-life-os-instance.amazonaws.com"

# Life OS API Key for authentication
export LIFE_OS_API_KEY="your-api-key-here"

# Optional: Set log level (debug, info, warn, error)
export LOG_LEVEL="info"
```

Or add to your `.env` file:

```env
LIFE_OS_API_URL=https://your-life-os-instance.amazonaws.com
LIFE_OS_API_KEY=your-api-key-here
LOG_LEVEL=info
```

### 3. Register the Skill

In your Clawdbot configuration, register the Life OS skill:

```javascript
// clawdbot.config.js
import lifeOsSkill from './skills/life-os/life-os.js';

export default {
  skills: [
    lifeOsSkill,
    // ... other skills
  ],
};
```

Or if using a skill loader:

```javascript
// In your skill loader
const skills = await loadSkills('./skills');
bot.registerSkills(skills);
```

## Configuration

### Trigger Keywords

The skill triggers on messages containing these keyword categories:

| Category | Keywords |
|----------|----------|
| Content | write, create, draft, compose, blog, article, post, content, copy, script, outline |
| Research | research, analyze, investigate, study, find, search, lookup, pubmed, papers, literature |
| Social | twitter, tweet, x post, linkedin, social, thread, viral, engagement |
| Finance | finance, loan, mortgage, investment, budget, expense, income, tax, savings, portfolio |
| HR | hr, human resources, employee, hiring, recruit, onboard, payroll, benefits, performance |
| Health | health, medical, doctor, appointment, medication, wellness, fitness, nutrition, symptom |
| Tasks | task, todo, schedule, calendar, reminder, deadline, project, milestone |

### Customizing Triggers

Edit `life-os.config.js` to add or modify trigger keywords:

```javascript
// life-os.config.js
export const config = {
  triggers: {
    content: [
      'write', 'create', 'draft',
      // Add your custom keywords
      'copywriting', 'newsletter',
    ],
    // ...
  },
};
```

### Timeout Configuration

Adjust timeouts based on your network conditions:

```javascript
timeouts: {
  default: 30000,    // 30 seconds for most requests
  extended: 120000,  // 2 minutes for research/content
  health: 5000,      // 5 seconds for health checks
},
```

### Retry Configuration

Configure retry behavior for resilience:

```javascript
retry: {
  maxAttempts: 3,
  initialDelay: 1000,
  backoffMultiplier: 2,
  maxDelay: 10000,
},
```

## Usage

Once installed, the skill automatically intercepts relevant messages:

```
User: Can you write a blog post about AI trends?
Clawdbot: [Routes to Life OS Content Orchestrator, returns formatted response]

User: Research the latest papers on CRISPR
Clawdbot: [Routes to Life OS Research Orchestrator, returns findings]

User: What's my loan balance?
Clawdbot: [Routes to Life OS Finance Orchestrator, returns financial data]
```

## API Reference

### Skill Object

```javascript
import lifeOsSkill from './life-os.js';

// Properties
lifeOsSkill.name          // 'life-os'
lifeOsSkill.description   // Skill description
lifeOsSkill.version       // '1.0.0'
lifeOsSkill.triggers      // Array of trigger keywords

// Methods
lifeOsSkill.shouldTrigger(message)    // Check if message should trigger
lifeOsSkill.getCategories(message)    // Get matched categories
lifeOsSkill.handler(context)          // Process message
lifeOsSkill.checkHealth()             // Check Life OS health
```

### Handler Context

```javascript
const context = {
  message: "Write a blog post about AI",
  userId: "user-123",
  conversationId: "conv-456",
  metadata: {
    // Additional context
  },
};

const result = await lifeOsSkill.handler(context);
```

### Response Format

```javascript
// Success
{
  success: true,
  response: "Here's your blog post...",
  metadata: {
    orchestrator: "content",
    categories: ["content"],
    processingTime: 1234,
  },
}

// Error
{
  success: false,
  response: "Friendly error message",
  error: {
    message: "Technical error details",
    categories: ["content"],
  },
}
```

## Testing

### Health Check

Test connectivity to Life OS:

```bash
npm run check-health
```

Or programmatically:

```javascript
import { checkHealth } from './life-os.js';

const isHealthy = await checkHealth();
console.log('Life OS status:', isHealthy ? 'healthy' : 'unavailable');
```

### Test Message Processing

```javascript
import lifeOsSkill from './life-os.js';

// Test trigger detection
console.log(lifeOsSkill.shouldTrigger('Write a blog post'));  // true
console.log(lifeOsSkill.shouldTrigger('Hello there'));        // false

// Test category detection
console.log(lifeOsSkill.getCategories('Research AI papers'));
// ['research']

// Test full processing
const result = await lifeOsSkill.handler({
  message: 'Create a Twitter thread about productivity',
  userId: 'test-user',
});
console.log(result);
```

### Manual API Test

```bash
curl -X POST "${LIFE_OS_API_URL}/api/v1/route" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${LIFE_OS_API_KEY}" \
  -d '{"message": "Write a short blog post about testing", "context": {"source": "test"}}'
```

## Troubleshooting

### Connection Refused

**Symptom**: `ECONNREFUSED` error

**Solutions**:
1. Verify `LIFE_OS_API_URL` is correct
2. Check if Life OS is running on AWS
3. Verify security groups allow traffic from VPS IP
4. Check if using correct protocol (http vs https)

### Authentication Failed

**Symptom**: 401 or 403 errors

**Solutions**:
1. Verify `LIFE_OS_API_KEY` is set correctly
2. Check API key hasn't expired
3. Regenerate API key if needed

### Timeout Errors

**Symptom**: Request timeout after X ms

**Solutions**:
1. Increase timeout values in config
2. Check network latency between VPS and AWS
3. Check Life OS isn't overloaded
4. Consider using extended timeout for complex operations

### No Response

**Symptom**: Empty or undefined response

**Solutions**:
1. Enable debug logging: `LOG_LEVEL=debug`
2. Check Life OS logs for errors
3. Verify the orchestrator is handling the request type

### Rate Limiting

**Symptom**: 429 errors

**Solutions**:
1. Implement request queuing
2. Increase retry delays
3. Contact admin to increase rate limits

## Logging

Enable debug logging for troubleshooting:

```bash
export LOG_LEVEL=debug
```

Log levels:
- `debug`: All messages including request/response details
- `info`: General operational messages
- `warn`: Warnings and retry attempts
- `error`: Errors only

## Security Considerations

1. **API Key Storage**: Store `LIFE_OS_API_KEY` securely, never commit to version control
2. **HTTPS**: Always use HTTPS for the API URL in production
3. **IP Whitelisting**: Configure AWS security groups to only allow VPS IP
4. **Key Rotation**: Rotate API keys periodically

## Architecture

```
+-------------+     +------------------+     +------------------+
|  Clawdbot   | --> | Life OS Skill    | --> | Life OS Master   |
|  (VPS)      |     | (This Package)   |     | Router (AWS)     |
+-------------+     +------------------+     +------------------+
                                                     |
                           +-------------------------+
                           |
            +--------------+--------------+
            |              |              |
       +----v----+   +-----v-----+  +-----v-----+
       | Content |   | Research  |  | Finance   |
       | Orch.   |   | Orch.     |  | Orch.     |
       +---------+   +-----------+  +-----------+
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

MIT License
