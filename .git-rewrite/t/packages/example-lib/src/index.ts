/**
 * @fileoverview Example TypeScript library for Core Nexus monorepo validation
 * @author Tyvonne Boykin <tyvonne@vonbase.com>
 */

export interface User {
  id: string;
  name: string;
  email: string;
  createdAt: Date;
  isActive: boolean;
}

export interface CreateUserInput {
  name: string;
  email: string;
}

export interface UserService {
  createUser(input: CreateUserInput): Promise<User>;
  getUser(id: string): Promise<User | null>;
  updateUser(id: string, updates: Partial<Omit<User, 'id' | 'createdAt'>>): Promise<User>;
  deleteUser(id: string): Promise<boolean>;
  listUsers(limit?: number): Promise<User[]>;
}

/**
 * In-memory implementation of UserService for demonstration
 */
export class MemoryUserService implements UserService {
  private users = new Map<string, User>();
  private idCounter = 1;

  /**
   * Creates a new user
   */
  async createUser(input: CreateUserInput): Promise<User> {
    if (!input.name || !input.email) {
      throw new Error('Name and email are required');
    }

    if (!this.isValidEmail(input.email)) {
      throw new Error('Invalid email format');
    }

    // Check for duplicate email
    const existingUser = Array.from(this.users.values()).find(
      (user) => user.email === input.email
    );
    if (existingUser) {
      throw new Error('User with this email already exists');
    }

    const user: User = {
      id: this.generateId(),
      name: input.name.trim(),
      email: input.email.toLowerCase().trim(),
      createdAt: new Date(),
      isActive: true,
    };

    this.users.set(user.id, user);
    return user;
  }

  /**
   * Retrieves a user by ID
   */
  async getUser(id: string): Promise<User | null> {
    if (!id) {
      throw new Error('User ID is required');
    }
    return this.users.get(id) || null;
  }

  /**
   * Updates an existing user
   */
  async updateUser(id: string, updates: Partial<Omit<User, 'id' | 'createdAt'>>): Promise<User> {
    const user = await this.getUser(id);
    if (!user) {
      throw new Error(`User with ID ${id} not found`);
    }

    if (updates.email && !this.isValidEmail(updates.email)) {
      throw new Error('Invalid email format');
    }

    // Check for duplicate email if email is being updated
    if (updates.email && updates.email !== user.email) {
      const existingUser = Array.from(this.users.values()).find(
        (u) => u.email === updates.email && u.id !== id
      );
      if (existingUser) {
        throw new Error('User with this email already exists');
      }
    }

    const updatedUser: User = {
      ...user,
      ...updates,
      id: user.id, // Ensure ID cannot be changed
      createdAt: user.createdAt, // Ensure createdAt cannot be changed
      email: updates.email ? updates.email.toLowerCase().trim() : user.email,
      name: updates.name ? updates.name.trim() : user.name,
    };

    this.users.set(id, updatedUser);
    return updatedUser;
  }

  /**
   * Deletes a user
   */
  async deleteUser(id: string): Promise<boolean> {
    if (!id) {
      throw new Error('User ID is required');
    }
    return this.users.delete(id);
  }

  /**
   * Lists all users with optional limit
   */
  async listUsers(limit?: number): Promise<User[]> {
    const users = Array.from(this.users.values());
    users.sort((a, b) => a.createdAt.getTime() - b.createdAt.getTime());
    return limit ? users.slice(0, limit) : users;
  }

  /**
   * Gets the total number of users
   */
  async getUserCount(): Promise<number> {
    return this.users.size;
  }

  /**
   * Clears all users (useful for testing)
   */
  async clear(): Promise<void> {
    this.users.clear();
    this.idCounter = 1;
  }

  private generateId(): string {
    return `user_${this.idCounter++}`;
  }

  private isValidEmail(email: string): boolean {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
  }
}

/**
 * Utility functions for working with users
 */
export const UserUtils = {
  /**
   * Formats a user's display name
   */
  getDisplayName(user: User): string {
    return user.name;
  },

  /**
   * Checks if a user is recently created (within last 24 hours)
   */
  isRecentlyCreated(user: User): boolean {
    const oneDayAgo = new Date(Date.now() - 24 * 60 * 60 * 1000);
    return user.createdAt > oneDayAgo;
  },

  /**
   * Gets user initials
   */
  getInitials(user: User): string {
    return user.name
      .split(' ')
      .map((part) => part.charAt(0).toUpperCase())
      .join('')
      .slice(0, 2);
  },

  /**
   * Validates user data
   */
  validateUser(user: Partial<User>): string[] {
    const errors: string[] = [];

    if (!user.name || user.name.trim().length === 0) {
      errors.push('Name is required');
    }

    if (!user.email || user.email.trim().length === 0) {
      errors.push('Email is required');
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(user.email)) {
      errors.push('Invalid email format');
    }

    return errors;
  },
};

// Export a default instance for convenience
export const userService = new MemoryUserService();

// Re-export everything for convenience
export * from './index';
export default MemoryUserService;