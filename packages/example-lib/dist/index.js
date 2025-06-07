// src/index.ts
var MemoryUserService = class {
  users = /* @__PURE__ */ new Map();
  idCounter = 1;
  /**
   * Creates a new user
   */
  async createUser(input) {
    if (!input.name || !input.email) {
      throw new Error("Name and email are required");
    }
    if (!this.isValidEmail(input.email)) {
      throw new Error("Invalid email format");
    }
    const existingUser = Array.from(this.users.values()).find(
      (user2) => user2.email === input.email
    );
    if (existingUser) {
      throw new Error("User with this email already exists");
    }
    const user = {
      id: this.generateId(),
      name: input.name.trim(),
      email: input.email.toLowerCase().trim(),
      createdAt: /* @__PURE__ */ new Date(),
      isActive: true
    };
    this.users.set(user.id, user);
    return user;
  }
  /**
   * Retrieves a user by ID
   */
  async getUser(id) {
    if (!id) {
      throw new Error("User ID is required");
    }
    return this.users.get(id) || null;
  }
  /**
   * Updates an existing user
   */
  async updateUser(id, updates) {
    const user = await this.getUser(id);
    if (!user) {
      throw new Error(`User with ID ${id} not found`);
    }
    if (updates.email && !this.isValidEmail(updates.email)) {
      throw new Error("Invalid email format");
    }
    if (updates.email && updates.email !== user.email) {
      const existingUser = Array.from(this.users.values()).find(
        (u) => u.email === updates.email && u.id !== id
      );
      if (existingUser) {
        throw new Error("User with this email already exists");
      }
    }
    const updatedUser = {
      ...user,
      ...updates,
      id: user.id,
      // Ensure ID cannot be changed
      createdAt: user.createdAt,
      // Ensure createdAt cannot be changed
      email: updates.email ? updates.email.toLowerCase().trim() : user.email,
      name: updates.name ? updates.name.trim() : user.name
    };
    this.users.set(id, updatedUser);
    return updatedUser;
  }
  /**
   * Deletes a user
   */
  async deleteUser(id) {
    if (!id) {
      throw new Error("User ID is required");
    }
    return this.users.delete(id);
  }
  /**
   * Lists all users with optional limit
   */
  async listUsers(limit) {
    const users = Array.from(this.users.values());
    users.sort((a, b) => a.createdAt.getTime() - b.createdAt.getTime());
    return limit ? users.slice(0, limit) : users;
  }
  /**
   * Gets the total number of users
   */
  async getUserCount() {
    return this.users.size;
  }
  /**
   * Clears all users (useful for testing)
   */
  async clear() {
    this.users.clear();
    this.idCounter = 1;
  }
  generateId() {
    return `user_${this.idCounter++}`;
  }
  isValidEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
  }
};
var UserUtils = {
  /**
   * Formats a user's display name
   */
  getDisplayName(user) {
    return user.name;
  },
  /**
   * Checks if a user is recently created (within last 24 hours)
   */
  isRecentlyCreated(user) {
    const oneDayAgo = new Date(Date.now() - 24 * 60 * 60 * 1e3);
    return user.createdAt > oneDayAgo;
  },
  /**
   * Gets user initials
   */
  getInitials(user) {
    return user.name.split(" ").map((part) => part.charAt(0).toUpperCase()).join("").slice(0, 2);
  },
  /**
   * Validates user data
   */
  validateUser(user) {
    const errors = [];
    if (!user.name || user.name.trim().length === 0) {
      errors.push("Name is required");
    }
    if (!user.email || user.email.trim().length === 0) {
      errors.push("Email is required");
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(user.email)) {
      errors.push("Invalid email format");
    }
    return errors;
  }
};
var userService = new MemoryUserService();
var index_default = MemoryUserService;
export {
  MemoryUserService,
  UserUtils,
  index_default as default,
  userService
};
