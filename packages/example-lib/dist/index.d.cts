/**
 * @fileoverview Example TypeScript library for Core Nexus monorepo validation
 * @author Tyvonne Boykin <tyvonne@vonbase.com>
 */
interface User {
    id: string;
    name: string;
    email: string;
    createdAt: Date;
    isActive: boolean;
}
interface CreateUserInput {
    name: string;
    email: string;
}
interface UserService {
    createUser(input: CreateUserInput): Promise<User>;
    getUser(id: string): Promise<User | null>;
    updateUser(id: string, updates: Partial<Omit<User, 'id' | 'createdAt'>>): Promise<User>;
    deleteUser(id: string): Promise<boolean>;
    listUsers(limit?: number): Promise<User[]>;
}
/**
 * In-memory implementation of UserService for demonstration
 */
declare class MemoryUserService implements UserService {
    private users;
    private idCounter;
    /**
     * Creates a new user
     */
    createUser(input: CreateUserInput): Promise<User>;
    /**
     * Retrieves a user by ID
     */
    getUser(id: string): Promise<User | null>;
    /**
     * Updates an existing user
     */
    updateUser(id: string, updates: Partial<Omit<User, 'id' | 'createdAt'>>): Promise<User>;
    /**
     * Deletes a user
     */
    deleteUser(id: string): Promise<boolean>;
    /**
     * Lists all users with optional limit
     */
    listUsers(limit?: number): Promise<User[]>;
    /**
     * Gets the total number of users
     */
    getUserCount(): Promise<number>;
    /**
     * Clears all users (useful for testing)
     */
    clear(): Promise<void>;
    private generateId;
    private isValidEmail;
}
/**
 * Utility functions for working with users
 */
declare const UserUtils: {
    /**
     * Formats a user's display name
     */
    getDisplayName(user: User): string;
    /**
     * Checks if a user is recently created (within last 24 hours)
     */
    isRecentlyCreated(user: User): boolean;
    /**
     * Gets user initials
     */
    getInitials(user: User): string;
    /**
     * Validates user data
     */
    validateUser(user: Partial<User>): string[];
};
declare const userService: MemoryUserService;

export { type CreateUserInput, MemoryUserService, type User, type UserService, UserUtils, MemoryUserService as default, userService };
