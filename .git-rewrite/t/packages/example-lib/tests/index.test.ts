/**
 * @fileoverview Tests for example-lib User service and utilities
 * @author Tyvonne Boykin <tyvonne@vonbase.com>
 */

import { describe, it, expect, beforeEach } from 'vitest';
import {
  User,
  CreateUserInput,
  MemoryUserService,
  UserUtils,
  userService
} from '../src/index';

describe('MemoryUserService', () => {
  let service: MemoryUserService;

  beforeEach(async () => {
    service = new MemoryUserService();
    await service.clear();
  });

  describe('createUser', () => {
    it('should create a valid user', async () => {
      const input: CreateUserInput = {
        name: 'John Doe',
        email: 'john@example.com'
      };

      const user = await service.createUser(input);

      expect(user.id).toBeTruthy();
      expect(user.name).toBe('John Doe');
      expect(user.email).toBe('john@example.com');
      expect(user.isActive).toBe(true);
      expect(user.createdAt).toBeInstanceOf(Date);
    });

    it('should throw error for invalid email', async () => {
      const input: CreateUserInput = {
        name: 'John Doe',
        email: 'invalid-email'
      };

      await expect(service.createUser(input)).rejects.toThrow('Invalid email format');
    });

    it('should throw error for duplicate email', async () => {
      const input: CreateUserInput = {
        name: 'John Doe',
        email: 'john@example.com'
      };

      await service.createUser(input);
      await expect(service.createUser(input)).rejects.toThrow('User with this email already exists');
    });

    it('should throw error for empty name', async () => {
      const input: CreateUserInput = {
        name: '',
        email: 'john@example.com'
      };

      await expect(service.createUser(input)).rejects.toThrow('Name and email are required');
    });

    it('should normalize email to lowercase', async () => {
      const input: CreateUserInput = {
        name: 'John Doe',
        email: 'JOHN@EXAMPLE.COM'
      };

      const user = await service.createUser(input);
      expect(user.email).toBe('john@example.com');
    });
  });

  describe('getUser', () => {
    it('should retrieve existing user', async () => {
      const input: CreateUserInput = {
        name: 'John Doe',
        email: 'john@example.com'
      };

      const createdUser = await service.createUser(input);
      const retrievedUser = await service.getUser(createdUser.id);

      expect(retrievedUser).toEqual(createdUser);
    });

    it('should return null for non-existent user', async () => {
      const user = await service.getUser('non-existent-id');
      expect(user).toBeNull();
    });

    it('should throw error for empty ID', async () => {
      await expect(service.getUser('')).rejects.toThrow('User ID is required');
    });
  });

  describe('updateUser', () => {
    it('should update user successfully', async () => {
      const input: CreateUserInput = {
        name: 'John Doe',
        email: 'john@example.com'
      };

      const user = await service.createUser(input);
      const updatedUser = await service.updateUser(user.id, {
        name: 'Jane Doe',
        isActive: false
      });

      expect(updatedUser.name).toBe('Jane Doe');
      expect(updatedUser.email).toBe('john@example.com');
      expect(updatedUser.isActive).toBe(false);
      expect(updatedUser.id).toBe(user.id);
      expect(updatedUser.createdAt).toEqual(user.createdAt);
    });

    it('should throw error for non-existent user', async () => {
      await expect(service.updateUser('non-existent', { name: 'Test' }))
        .rejects.toThrow('User with ID non-existent not found');
    });

    it('should validate email during update', async () => {
      const input: CreateUserInput = {
        name: 'John Doe',
        email: 'john@example.com'
      };

      const user = await service.createUser(input);
      await expect(service.updateUser(user.id, { email: 'invalid' }))
        .rejects.toThrow('Invalid email format');
    });

    it('should prevent duplicate email during update', async () => {
      const user1 = await service.createUser({
        name: 'John Doe',
        email: 'john@example.com'
      });

      const user2 = await service.createUser({
        name: 'Jane Doe',
        email: 'jane@example.com'
      });

      await expect(service.updateUser(user2.id, { email: 'john@example.com' }))
        .rejects.toThrow('User with this email already exists');
    });
  });

  describe('deleteUser', () => {
    it('should delete existing user', async () => {
      const input: CreateUserInput = {
        name: 'John Doe',
        email: 'john@example.com'
      };

      const user = await service.createUser(input);
      const deleted = await service.deleteUser(user.id);

      expect(deleted).toBe(true);
      
      const retrievedUser = await service.getUser(user.id);
      expect(retrievedUser).toBeNull();
    });

    it('should return false for non-existent user', async () => {
      const deleted = await service.deleteUser('non-existent');
      expect(deleted).toBe(false);
    });

    it('should throw error for empty ID', async () => {
      await expect(service.deleteUser('')).rejects.toThrow('User ID is required');
    });
  });

  describe('listUsers', () => {
    it('should return all users sorted by creation date', async () => {
      const users = await Promise.all([
        service.createUser({ name: 'User 1', email: 'user1@example.com' }),
        service.createUser({ name: 'User 2', email: 'user2@example.com' }),
        service.createUser({ name: 'User 3', email: 'user3@example.com' })
      ]);

      const listedUsers = await service.listUsers();
      expect(listedUsers).toHaveLength(3);
      expect(listedUsers[0].createdAt.getTime()).toBeLessThanOrEqual(listedUsers[1].createdAt.getTime());
      expect(listedUsers[1].createdAt.getTime()).toBeLessThanOrEqual(listedUsers[2].createdAt.getTime());
    });

    it('should respect limit parameter', async () => {
      await Promise.all([
        service.createUser({ name: 'User 1', email: 'user1@example.com' }),
        service.createUser({ name: 'User 2', email: 'user2@example.com' }),
        service.createUser({ name: 'User 3', email: 'user3@example.com' })
      ]);

      const listedUsers = await service.listUsers(2);
      expect(listedUsers).toHaveLength(2);
    });

    it('should return empty array when no users exist', async () => {
      const listedUsers = await service.listUsers();
      expect(listedUsers).toHaveLength(0);
    });
  });

  describe('getUserCount', () => {
    it('should return correct user count', async () => {
      expect(await service.getUserCount()).toBe(0);

      await service.createUser({ name: 'User 1', email: 'user1@example.com' });
      expect(await service.getUserCount()).toBe(1);

      await service.createUser({ name: 'User 2', email: 'user2@example.com' });
      expect(await service.getUserCount()).toBe(2);
    });
  });

  describe('clear', () => {
    it('should clear all users', async () => {
      await service.createUser({ name: 'User 1', email: 'user1@example.com' });
      await service.createUser({ name: 'User 2', email: 'user2@example.com' });

      expect(await service.getUserCount()).toBe(2);

      await service.clear();
      expect(await service.getUserCount()).toBe(0);
    });
  });
});

describe('UserUtils', () => {
  const testUser: User = {
    id: 'user_1',
    name: 'John Doe',
    email: 'john@example.com',
    createdAt: new Date(),
    isActive: true
  };

  describe('getDisplayName', () => {
    it('should return user name', () => {
      expect(UserUtils.getDisplayName(testUser)).toBe('John Doe');
    });
  });

  describe('isRecentlyCreated', () => {
    it('should return true for recently created user', () => {
      const recentUser = { ...testUser, createdAt: new Date() };
      expect(UserUtils.isRecentlyCreated(recentUser)).toBe(true);
    });

    it('should return false for old user', () => {
      const oldUser = { 
        ...testUser, 
        createdAt: new Date(Date.now() - 25 * 60 * 60 * 1000) // 25 hours ago
      };
      expect(UserUtils.isRecentlyCreated(oldUser)).toBe(false);
    });
  });

  describe('getInitials', () => {
    it('should return initials for two names', () => {
      expect(UserUtils.getInitials(testUser)).toBe('JD');
    });

    it('should return initials for single name', () => {
      const singleNameUser = { ...testUser, name: 'John' };
      expect(UserUtils.getInitials(singleNameUser)).toBe('J');
    });

    it('should return first two initials for multiple names', () => {
      const multiNameUser = { ...testUser, name: 'John Michael Doe' };
      expect(UserUtils.getInitials(multiNameUser)).toBe('JM');
    });
  });

  describe('validateUser', () => {
    it('should return no errors for valid user', () => {
      const errors = UserUtils.validateUser(testUser);
      expect(errors).toHaveLength(0);
    });

    it('should return error for missing name', () => {
      const errors = UserUtils.validateUser({ ...testUser, name: '' });
      expect(errors).toContain('Name is required');
    });

    it('should return error for missing email', () => {
      const errors = UserUtils.validateUser({ ...testUser, email: '' });
      expect(errors).toContain('Email is required');
    });

    it('should return error for invalid email', () => {
      const errors = UserUtils.validateUser({ ...testUser, email: 'invalid' });
      expect(errors).toContain('Invalid email format');
    });

    it('should return multiple errors', () => {
      const errors = UserUtils.validateUser({ ...testUser, name: '', email: 'invalid' });
      expect(errors).toHaveLength(2);
      expect(errors).toContain('Name is required');
      expect(errors).toContain('Invalid email format');
    });
  });
});

describe('Default Export', () => {
  it('should export userService instance', () => {
    expect(userService).toBeInstanceOf(MemoryUserService);
  });
});