// Utility function to fetch user profile
const fetchProfile = async (id) => {
    const response = await fetch(`/api/profile/${id}`);
    if (!response.ok) throw new Error('Failed to fetch profile');
    return await response.json();
};

export { fetchProfile };