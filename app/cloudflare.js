// ---------------------------------------------------------------------------
// Configuration
// ---------------------------------------------------------------------------
// Use the fastest generally-available chat model on Workers AI.
// Centralising the value here makes it trivial to experiment with other
// models (e.g. `@cf/meta/llama-3.3-70b-instruct-fp8-fast`) without touching
// the business logic below.
const MODEL_NAME = '@cf/meta/llama-3.1-8b-instruct-fast';

export default {
  /**
   * Primary fetch handler used by Cloudflare Workers.
   *
   * This implementation supports the following request patterns:
   *  1.  POST /jarvis            –  JSON body: { "question": "..." }
   *  2.  POST /jarvis            –  multipart/form-data with a single "file" field (future-proofed)
   *  3.  POST / (or any path)    –  Legacy JSON body: { "inputs": [{ "prompt": "..." }, ...] }
   */
  async fetch(request, env) {
    const { method } = request;

    // Handle CORS pre-flight requests --------------------------------------
    if (method === 'OPTIONS') {
      return new Response(null, {
        status: 204,
        headers: {
          'Access-Control-Allow-Origin': '*',
          'Access-Control-Allow-Methods': 'POST, OPTIONS',
          'Access-Control-Allow-Headers': 'Content-Type',
          'Access-Control-Max-Age': '86400'
        }
      });
    }

    // For convenience allow a simple GET to return service status ----------
    if (method === 'GET') {
      const html = `
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Jarvis AI Chat</title>
            <style>
                * {
                    margin: 0;
                    padding: 0;
                    box-sizing: border-box;
                }
                
                body {
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    background-color: #ffffff;
                    color: #333;
                    line-height: 1.6;
                    height: 100vh;
                    display: flex;
                    flex-direction: column;
                }

                .chat-container {
                    max-width: 800px;
                    margin: 0 auto;
                    padding: 20px;
                    height: 100%;
                    display: flex;
                    flex-direction: column;
                }

                h1 {
                    font-size: 1.5rem;
                    font-weight: 500;
                    color: #666;
                    margin-bottom: 20px;
                    text-align: center;
                }

                .chat-messages {
                    flex-grow: 1;
                    overflow-y: auto;
                    padding: 20px 0;
                    display: flex;
                    flex-direction: column;
                    gap: 12px;
                }

                .message {
                    max-width: 85%;
                    padding: 12px 16px;
                    border-radius: 12px;
                    font-size: 0.95rem;
                    line-height: 1.5;
                }

                .user-message {
                    background-color: #007AFF;
                    color: white;
                    align-self: flex-end;
                    border-bottom-right-radius: 4px;
                }

                .ai-message {
                    background-color: #f0f0f0;
                    color: #333;
                    align-self: flex-start;
                    border-bottom-left-radius: 4px;
                }

                .input-container {
                    display: flex;
                    gap: 8px;
                    padding: 20px 0;
                    border-top: 1px solid #eee;
                }

                #messageInput {
                    flex-grow: 1;
                    padding: 12px 16px;
                    border: 1px solid #ddd;
                    border-radius: 20px;
                    font-size: 0.95rem;
                    outline: none;
                    transition: border-color 0.2s;
                }

                #messageInput:focus {
                    border-color: #007AFF;
                }

                button {
                    padding: 12px 24px;
                    background-color: #007AFF;
                    color: white;
                    border: none;
                    border-radius: 20px;
                    font-size: 0.95rem;
                    cursor: pointer;
                    transition: background-color 0.2s;
                }

                button:hover {
                    background-color: #0056b3;
                }

                @media (max-width: 600px) {
                    .chat-container {
                        padding: 10px;
                    }
                    
                    .message {
                        max-width: 90%;
                    }
                }
            </style>
        </head>
        <body>
            <div class="chat-container">
                <h1>Jarvis AI</h1>
                <div class="chat-messages" id="chatMessages"></div>
                <div class="input-container">
                    <input type="text" id="messageInput" placeholder="Ask me anything..." autocomplete="off">
                    <button onclick="sendMessage()">Send</button>
                </div>
            </div>

            <script>
                async function sendMessage() {
                    const input = document.getElementById('messageInput');
                    const message = input.value.trim();
                    if (!message) return;

                    addMessage(message, 'user');
                    input.value = '';

                    try {
                        const response = await fetch('/jarvis', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json'
                            },
                            body: JSON.stringify({ question: message })
                        });

                        const data = await response.json();
                        addMessage(data.answer, 'ai');

                        if (data.sources && data.sources.length > 0) {
                            const sourcesText = 'Sources:\\n' + data.sources.map(s => 
                                \`- \${s.title}: \${s.url}\`
                            ).join('\\n');
                            addMessage(sourcesText, 'ai');
                        }
                    } catch (error) {
                        addMessage('Error: ' + error.message, 'ai');
                    }
                }

                function addMessage(text, type) {
                    const messagesDiv = document.getElementById('chatMessages');
                    const messageDiv = document.createElement('div');
                    messageDiv.className = \`message \${type}-message\`;
                    messageDiv.textContent = text;
                    messagesDiv.appendChild(messageDiv);
                    messagesDiv.scrollTop = messagesDiv.scrollHeight;
                }

                document.getElementById('messageInput').addEventListener('keypress', function(e) {
                    if (e.key === 'Enter') {
                        sendMessage();
                    }
                });
            </script>
        </body>
        </html>
      `;

      return new Response(html, {
        headers: {
          'Content-Type': 'text/html',
          'Access-Control-Allow-Origin': '*'
        }
      });
    }

    // Only accept POST requests for AI interaction beyond this point.
    if (method !== 'POST') {
      return new Response('Method not allowed', { status: 405, headers: { 'Access-Control-Allow-Origin': '*' } });
    }

    const { pathname } = new URL(request.url);

    try {
      // Handle the modern endpoint used by AI.html
      if (pathname === '/jarvis' || pathname === '/ai/jarvis') {
        const contentType = request.headers.get('content-type') || '';

        // 1) JSON body with a "question" field
        if (contentType.includes('application/json')) {
          const body = await request.json();

          // ------------------------------------------------------------------
          // 1A) Legacy payload support: { "inputs": [ { prompt: "..." } ] }
          // ------------------------------------------------------------------
          if (Array.isArray(body.inputs)) {
            const tasks = [];
            for (const input of body.inputs) {
              if (input.prompt) {
                const ai = await env.AI.run(MODEL_NAME, { prompt: input.prompt });
                // Return only the model text so downstream code expects a string
                tasks.push({ inputs: input, response: ai.response, usage: ai.usage });
              } else if (input.messages) {
                const ai = await env.AI.run(MODEL_NAME, { messages: input.messages });
                tasks.push({ inputs: input, response: ai.response, usage: ai.usage });
              }
            }

            return new Response(JSON.stringify(tasks), {
              headers: {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
              }
            });
          }

          // ------------------------------------------------------------------
          // 1B) Modern payload: { "question": "..." }
          // ------------------------------------------------------------------
          if (typeof body.question !== 'string' || !body.question.trim()) {
            return new Response('Invalid request – missing "question" field', { status: 400 });
          }

          const prompt = body.question.trim();

          // --- Basic knowledge-base lookup --------------------------------
          const ARTICLES = [
            {
              title: 'Oralyzer Overview',
              url: 'https://docs.pdshealth.com/oralyzer/overview',
              keywords: ['oralyzer', 'overview', 'introduction']
            },
            {
              title: 'Using Oralyzer for Rapid Diagnostics',
              url: 'https://docs.pdshealth.com/oralyzer/rapid-diagnostics',
              keywords: ['oralyzer', 'diagnostics', 'usage', 'rapid']
            },
            {
              title: 'Oralyzer FAQ',
              url: 'https://docs.pdshealth.com/oralyzer/faq',
              keywords: ['oralyzer', 'faq', 'questions', 'troubleshooting']
            }
          ];

          const lowerPrompt = prompt.toLowerCase();
          const scored = ARTICLES.map(a => {
            const matches = a.keywords.reduce((acc, kw) => acc + (lowerPrompt.includes(kw) ? 1 : 0), 0);
            return { ...a, score: matches };
          }).filter(a => a.score > 0).sort((a, b) => b.score - a.score);

          const topSources = scored.slice(0, 3).map(({ title, url }) => ({ title, url }));

          const aiResponse = await env.AI.run(MODEL_NAME, { prompt });

          return new Response(JSON.stringify({ answer: aiResponse.response, usage: aiResponse.usage, sources: topSources }), {
            headers: {
              'Content-Type': 'application/json',
              'Access-Control-Allow-Origin': '*'
            }
          });
        }

        // 2) multipart/form-data with an uploaded file (future extension)
        if (contentType.includes('multipart/form-data')) {
          const formData = await request.formData();
          const file = formData.get('file');

          if (!file) {
            return new Response('No file field found in form data', { status: 400 });
          }

          // TODO: Implement actual file processing / AI inference.
          // For now, we simply acknowledge receipt of the file.
          const placeholder = `Received file "${file.name}" (${file.type || 'unknown type'}). File processing is not yet implemented.`;

          return new Response(JSON.stringify({ answer: placeholder }), {
            headers: {
              'Content-Type': 'application/json',
              'Access-Control-Allow-Origin': '*'
            }
          });
        }

        // Unsupported content-type for /jarvis
        return new Response('Unsupported Content-Type', { status: 415, headers: { 'Access-Control-Allow-Origin': '*' } });
      }

      // ----- Legacy behaviour kept for backwards compatibility -----
      // Expecting JSON: { inputs: [ { prompt: "..." | messages: [...] }, ... ] }
      const { inputs } = await request.clone().json().catch(() => ({ inputs: undefined }));

      if (!Array.isArray(inputs)) {
        return new Response('Invalid request format', { status: 400 });
      }

      const tasks = [];
      for (const input of inputs) {
        if (input.prompt) {
          // Direct prompt scenario
          const response = await env.AI.run(MODEL_NAME, {
            prompt: input.prompt
          });
          tasks.push({ inputs: input, response });
        } else if (input.messages) {
          // OpenAI-style messages array
          const response = await env.AI.run(MODEL_NAME, {
            messages: input.messages
          });
          tasks.push({ inputs: input, response });
        }
      }

      return new Response(JSON.stringify(tasks), {
        headers: {
          'Content-Type': 'application/json',
          'Access-Control-Allow-Origin': '*'
        }
      });
    } catch (error) {
      return new Response('Error processing request: ' + error.message, { status: 500, headers: { 'Access-Control-Allow-Origin': '*' } });
    }
  }
};