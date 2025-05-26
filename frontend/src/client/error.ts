/**
 * Base exception for client A2A Client errors.
 */
export class A2AClientError extends Error {
    constructor(message: string) {
        super(message);
        this.name = 'A2AClientError';
        // Restore prototype chain for instanceof checks
        Object.setPrototypeOf(this, new.target.prototype);
    }
}

/**
 * Client exception for HTTP errors.
 */
export class A2AClientHTTPError extends A2AClientError {
    statusCode: number;
    message: string;

    constructor(statusCode: number, message: string) {
        super(`HTTP Error ${statusCode}: ${message}`);
        this.name = 'A2AClientHTTPError';
        this.statusCode = statusCode;
        this.message = message;
        // Restore prototype chain for instanceof checks
        Object.setPrototypeOf(this, new.target.prototype);
    }
}

/**
 * Client exception for JSON errors.
 */
export class A2AClientJSONError extends A2AClientError {
    message: string;

    constructor(message: string) {
        super(`JSON Error: ${message}`);
        this.name = 'A2AClientJSONError';
        this.message = message;
        // Restore prototype chain for instanceof checks
        Object.setPrototypeOf(this, new.target.prototype);
    }
} 