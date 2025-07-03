import { useEffect, useState } from "react";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

const usegetSubjectbyhStudent = () => {
    const token = localStorage.getItem('token');
    const entityId = localStorage.getItem('entity_id');
    const [subjects, setSubjects] = useState([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        const fetchSubjects = async () => {
            try {
                setIsLoading(true);
                const response = await fetch(`${API_BASE_URL}/subjects/student/${entityId}`, {
                    headers: {
                        'accept': 'application/json',
                        'Authorization': `Bearer ${token}`,
                    },
                });
                if (!response.ok) throw new Error('Failed to fetch subjects');
                const data = await response.json();
                setSubjects(data);
            } catch (error) {
                console.error('Error fetching subjects:', error);
                setError(error.message);
            } finally {
                setIsLoading(false);
            }
        };

        fetchSubjects();

        return () => {
            // Cleanup function
        };
    }, [entityId, token]);
    
    return { subjects, isLoading, error };
}

export default usegetSubjectbyhStudent
