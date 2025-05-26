import { v4 as uuidv4 } from 'uuid';
import type { Message, Part } from './schema';

/**
 * Create a Message object for the given role and content.
 */
export function createTextMessageObject(
    contextId: string,
    role: 'user' | 'agent' = 'user',
    content: string = '',
): Message {
    return {
        contextId,
        role,
        parts: [{ type: 'text', text: content } as Part],
        messageId: uuidv4(),
        type: 'message'
    };
}