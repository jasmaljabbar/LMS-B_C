

import { useEffect, useState } from "react";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

const useGetStudentbyID = (studentId) => {
    const [student, setStudent] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);   
    const token = localStorage.getItem('token');
    const entity_id = localStorage.getItem('entity_id');
    console.log(entity_id,"entity_id");

    const getStudentbyID = async (id) => {
        try {
            setLoading(true);
            const response = await fetch(`${API_BASE_URL}/students/${entity_id}`, {
                headers: {
                    'accept': 'application/json',
                    'Authorization': `Bearer ${token}`,
                },
            });            
            
            const data = await response.json();
            console.log(data,"data");
            setStudent(data);
            setLoading(false);

        } catch (error) {
            setError(error);
            setLoading(false);
        }
    }

    useEffect(() => {
        getStudentbyID();
    }, [entity_id]);

    return { student, loading, error };
}

export default useGetStudentbyID;
