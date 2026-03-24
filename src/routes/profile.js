const express = require('express');
const router = express.Router();

// Mock Database
const users = [{ id: 1, name: 'John Doe', email: 'john@example.com' }];

// API route to get user profile
router.get('/api/profile/:id', (req, res) => {
    const user = users.find(u => u.id === parseInt(req.params.id));
    if (!user) return res.status(404).send('User not found');
    res.send(user);
});

module.exports = router;