// Import necessary types from schema.ts
import type {
  // Core types
  AgentCard,
  JSONRPCRequest,
  Message,
  // Full Request types (needed for internal generics)
  SendMessageRequest,
  SendStreamingMessageRequest,
  GetTaskRequest,
  CancelTaskRequest,
  TaskResubscriptionRequest,
  SetTaskPushNotificationRequest,
  GetTaskPushNotificationRequest,
  // Specific Params types (used directly in public method signatures)
  TaskQueryParams, // Used by get, resubscribe
  TaskIdParams, // Used by cancel, getTaskPushNotificationConfig
  TaskPushNotificationConfig, // Used by setTaskPushNotificationConfig
  // Full Response types (needed for internal generics and result extraction)
  SendMessageResponse,
  SendMessageStreamingResponse,
  GetTaskResponse,
  CancelTaskResponse,
  SendTaskStreamingResponse,
  SetTaskPushNotificationResponse,
  GetTaskPushNotificationResponse,
  // Response Payload types (used in public method return signatures)
  Task,
  // Streaming Payload types (used in public method yield signatures)
  TaskStatusUpdateEvent,
  TaskArtifactUpdateEvent,
} from "./schema.ts";
import { A2AClientError, A2AClientHTTPError, A2AClientJSONError } from './error.ts';

/**
 * Agent Card resolver class
 */
export class A2ACardResolver {
  private baseUrl: string;
  private agentCardPath: string;
  private fetchImpl: typeof fetch;

  constructor(
    baseUrl: string,
    agentCardPath: string = '/.well-known/agent.json',
    fetchImpl: typeof fetch = fetch
  ) {
    this.baseUrl = baseUrl.endsWith('/') ? baseUrl.slice(0, -1) : baseUrl;
    this.agentCardPath = agentCardPath.startsWith('/') ? agentCardPath.slice(1) : agentCardPath;
    this.fetchImpl = fetchImpl.bind(window);
  }

  async getAgentCard(httpOptions: RequestInit = {}): Promise<AgentCard> {
    try {
      const response = await this.fetchImpl(
        `${this.baseUrl}/${this.agentCardPath}`,
        {
          ...httpOptions,
          method: 'GET',
          headers: {
            'Accept': 'application/json',
            ...(httpOptions.headers || {})
          }
        }
      );

      if (!response.ok) {
        throw new A2AClientHTTPError(response.status, response.statusText);
      }

      try {
        const data = await response.json();
        return data as AgentCard;
      } catch (e) {
        throw new A2AClientJSONError(e instanceof Error ? e.message : String(e));
      }
    } catch (e) {
      if (e instanceof A2AClientError) {
        throw e;
      }
      throw new A2AClientHTTPError(503, `Network communication error: ${e instanceof Error ? e.message : String(e)}`);
    }
  }
}

/**
 * A client implementation for the A2A protocol that communicates
 * with an A2A server over HTTP using JSON-RPC.
 */
export class A2AClient {
  private url: string;
  private fetchImpl: typeof fetch;
  private cachedAgentCard: AgentCard | null = null;

  constructor(options: { agentCard?: AgentCard; url?: string; fetchImpl?: typeof fetch }) {
    const { agentCard, url, fetchImpl = fetch } = options;

    if (agentCard) {
      this.url = agentCard.url;
    } else if (url) {
      this.url = url;
    } else {
      throw new Error('Must provide either agentCard or url');
    }

    this.fetchImpl = fetchImpl.bind(window);
  }

  /**
   * Creates an A2A client instance from an agent card URL
   */
  static async fromAgentCardUrl(
    baseUrl: string,
    agentCardPath: string = '/.well-known/agent.json',
    fetchImpl: typeof fetch = fetch,
    httpOptions: RequestInit = {}
  ): Promise<A2AClient> {
    const resolver = new A2ACardResolver(baseUrl, agentCardPath, fetchImpl);
    const agentCard = await resolver.getAgentCard(httpOptions);
    return new A2AClient({ agentCard, fetchImpl });
  }

  /**
   * Sends a message to the agent (non-streaming).
   */
  async sendMessage(message: Message, httpOptions: RequestInit = {}): Promise<Message | Task | null> {
    const request: SendMessageRequest = {
      jsonrpc: '2.0',
      id: crypto.randomUUID(),
      method: 'message/send',
      params: {
        message: message,
      }
    };

    const response = await this.sendRequest<SendMessageResponse>(request, httpOptions);
    return 'result' in response && response.result ? response.result : null;
  }

  /**
   * Sends a message and subscribes to streaming updates.
   */
  async *sendMessageStreaming(
    message: Message,
    httpOptions: RequestInit = {}
  ): AsyncGenerator<Message | Task | TaskStatusUpdateEvent | TaskArtifactUpdateEvent, void, unknown> {
    const request: SendStreamingMessageRequest = {
      jsonrpc: '2.0',
      id: crypto.randomUUID(),
      method: 'message/stream',
      params: {
        message: message,
      }
    };

    const response = await this.fetchImpl(this.url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'text/event-stream',
        ...(httpOptions.headers || {})
      },
      body: JSON.stringify(request),
      ...httpOptions
    });

    if (!response.ok) {
      throw new A2AClientHTTPError(response.status, response.statusText);
    }

    if (!response.body) {
      throw new A2AClientHTTPError(503, 'No response body received');
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6);
            try {
              const parsed = JSON.parse(data) as SendMessageStreamingResponse;
              if ('result' in parsed && parsed.result) {
                const result = parsed.result as unknown as Message | Task | TaskStatusUpdateEvent | TaskArtifactUpdateEvent;
                yield result;
              }
            } catch (e) {
              throw new A2AClientJSONError(`Failed to parse SSE data: ${e instanceof Error ? e.message : String(e)}`);
            }
          }
        }
      }
    } catch (e) {
      if (e instanceof A2AClientError) {
        throw e;
      }
      throw new A2AClientHTTPError(503, `Stream error: ${e instanceof Error ? e.message : String(e)}`);
    } finally {
      reader.releaseLock();
    }
  }

  /**
   * Sends a non-streaming JSON-RPC request to the agent (private).
   */
  private async sendRequest<T>(
    rpcRequestPayload: JSONRPCRequest,
    httpOptions: RequestInit = {}
  ): Promise<T> {
    try {
      const response = await this.fetchImpl(this.url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
          ...(httpOptions.headers || {})
        },
        body: JSON.stringify(rpcRequestPayload),
        ...httpOptions
      });

      if (!response.ok) {
        throw new A2AClientHTTPError(response.status, response.statusText);
      }

      try {
        return await response.json() as T;
      } catch (e) {
        throw new A2AClientJSONError(e instanceof Error ? e.message : String(e));
      }
    } catch (e) {
      if (e instanceof A2AClientError) {
        throw e;
      }
      throw new A2AClientHTTPError(503, `Network communication error: ${e instanceof Error ? e.message : String(e)}`);
    }
  }

  /**
   * Retrieves the current state of a task.
   */
  async getTask(params: TaskQueryParams, httpOptions: RequestInit = {}): Promise<Task | null> {
    const request: GetTaskRequest = {
      jsonrpc: '2.0',
      id: crypto.randomUUID(),
      method: 'tasks/get',
      params
    };

    const response = await this.sendRequest<GetTaskResponse>(request, httpOptions);
    return 'result' in response && response.result ? response.result : null;
  }

  /**
   * Cancels a currently running task.
   */
  async cancelTask(params: TaskIdParams, httpOptions: RequestInit = {}): Promise<Task | null> {
    const request: CancelTaskRequest = {
      jsonrpc: '2.0',
      id: crypto.randomUUID(),
      method: 'tasks/cancel',
      params
    };

    const response = await this.sendRequest<CancelTaskResponse>(request, httpOptions);
    return 'result' in response && response.result ? response.result : null;
  }

  /**
   * Sets or updates the push notification config for a task.
   */
  async setTaskPushNotification(
    params: TaskPushNotificationConfig,
    httpOptions: RequestInit = {}
  ): Promise<TaskPushNotificationConfig | null> {
    const request: SetTaskPushNotificationRequest = {
      jsonrpc: '2.0',
      id: crypto.randomUUID(),
      method: 'tasks/pushNotification/set',
      params
    };

    const response = await this.sendRequest<SetTaskPushNotificationResponse>(request, httpOptions);
    return 'result' in response && response.result ? response.result : null;
  }

  /**
   * Retrieves the currently configured push notification config for a task.
   */
  async getTaskPushNotification(
    params: TaskIdParams,
    httpOptions: RequestInit = {}
  ): Promise<TaskPushNotificationConfig | null> {
    const request: GetTaskPushNotificationRequest = {
      jsonrpc: '2.0',
      id: crypto.randomUUID(),
      method: 'tasks/pushNotification/get',
      params
    };

    const response = await this.sendRequest<GetTaskPushNotificationResponse>(request, httpOptions);
    return 'result' in response && response.result ? response.result : null;
  }

  /**
   * Resubscribes to updates for a task after a potential connection interruption.
   */
  async *resubscribeTask(
    params: TaskQueryParams,
    httpOptions: RequestInit = {}
  ): AsyncGenerator<TaskStatusUpdateEvent | TaskArtifactUpdateEvent, void, unknown> {
    const request: TaskResubscriptionRequest = {
      jsonrpc: '2.0',
      id: crypto.randomUUID(),
      method: 'tasks/resubscribe',
      params
    };

    const response = await this.fetchImpl(this.url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'text/event-stream',
        ...(httpOptions.headers || {})
      },
      body: JSON.stringify(request),
      ...httpOptions
    });

    if (!response.ok) {
      throw new A2AClientHTTPError(response.status, response.statusText);
    }

    if (!response.body) {
      throw new A2AClientHTTPError(503, 'No response body received');
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6);
            try {
              const parsed = JSON.parse(data) as SendTaskStreamingResponse;
              if ('result' in parsed && parsed.result) {
                yield parsed.result;
              }
            } catch (e) {
              throw new A2AClientJSONError(`Failed to parse SSE data: ${e instanceof Error ? e.message : String(e)}`);
            }
          }
        }
      }
    } catch (e) {
      if (e instanceof A2AClientError) {
        throw e;
      }
      throw new A2AClientHTTPError(503, `Stream error: ${e instanceof Error ? e.message : String(e)}`);
    } finally {
      reader.releaseLock();
    }
  }

  /**
   * Optional: Checks if the server likely supports optional methods based on agent card.
   * This is a client-side heuristic and might not be perfectly accurate.
   * @param capability The capability to check (e.g., 'streaming', 'pushNotifications').
   * @returns A promise resolving to true if the capability is likely supported.
   */
  async supports(capability: "streaming" | "pushNotifications"): Promise<boolean> {
    try {
      const card = await this.agentCard(); // Fetch card if not cached
      switch (capability) {
        // Check boolean flags directly on the capabilities object
        case "streaming":
          return !!card.capabilities?.streaming; // Use optional chaining and boolean conversion
        case "pushNotifications":
          return !!card.capabilities?.pushNotifications; // Use optional chaining and boolean conversion
        default:
          return false;
      }
    } catch (error) {
      console.error(
        `Failed to determine support for capability '${capability}':`,
        error
      );
      return false; // Assume not supported if card fetch fails
    }
  }

  /**
   * Retrieves the AgentCard.
   */
  async agentCard(): Promise<AgentCard> {
    if (this.cachedAgentCard) {
      return this.cachedAgentCard;
    }

    const resolver = new A2ACardResolver(this.url, '/.well-known/agent.json', this.fetchImpl);
    this.cachedAgentCard = await resolver.getAgentCard();
    return this.cachedAgentCard;
  }
}