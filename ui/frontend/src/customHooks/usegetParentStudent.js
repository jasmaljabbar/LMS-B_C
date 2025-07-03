import { useEffect, useState } from "react";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

const usegetParentStudent = () => {
    const [studentsData, setStudentsData] = useState();
    const [subjectsMap, setSubjectsMap] = useState({});
    const [lessonsMap, setLessonsMap] = useState({});

    useEffect(() => {
        const token = localStorage.getItem('token');
        const fetchData = async (token) => {
            try {
                const childrenResponse = await fetch(`${API_BASE_URL}/dashboard/parent/children`, {
                    headers: {
                        'accept': 'application/json',
                        'Authorization': `Bearer ${token}`,
                    },
                });
                const childrenData = await childrenResponse.json();
                if (childrenData.length > 0) {
                    setStudentsData(childrenData);
                }

            } catch (error) {
                console.error("Error fetching children data:", error);
            }
        };
        fetchData(token);
    }, []);

    const fetchLessonsForSubject = async (subjectId, token) => {
        try {
            const lessonsRes = await fetch(`${API_BASE_URL}/lessons/subject/${subjectId}`, {
                headers: {
                    'accept': 'application/json',
                    'Authorization': `Bearer ${token}`,
                },
            });

            const lessonsData = await lessonsRes.json();
            return lessonsData;
        } catch (error) {
            console.error(`Failed to fetch lessons for subject ${subjectId}`, error);
            return [];
        }
    };

    const fetchSubjectsForAll = async (token) => {
        const newSubjectsMap = {};
        const newLessonsMap = {};
        await Promise.all(
            studentsData && studentsData.map(async (student) => {
                try {
                    const res = await fetch(`${API_BASE_URL}/dashboard/parent/subject-performance/${student.student_id}`, {
                        headers: {
                            'accept': 'application/json',
                            'Authorization': `Bearer ${token}`,
                        },
                    });

                    const subjectData = await res.json();
                    newSubjectsMap[student.student_id] = subjectData;

                    // Fetch lessons for each subject
                    await Promise.all(
                        subjectData.map(async (subject) => {
                            const lessonsData = await fetchLessonsForSubject(subject.subject_id, token);
                            newLessonsMap[subject.subject_id] = lessonsData;
                        })
                    );

                } catch (error) {
                    console.error(`Failed to fetch subjects for ${student.student_id}`, error);
                }
            })
        );
        setSubjectsMap(newSubjectsMap);
        setLessonsMap(newLessonsMap);
    };

    // const fetchLessons = async (token) => {
    //     const newLessonsMap = {};
    //     await Promise.all(
    //         Object.keys(subjectsMap).map(async (studentId) => {
    //             const subjectData = subjectsMap[studentId];
    //             await Promise.all(
    //                 subjectData.map(async (subject) => {
    //                     const lessonsData = await fetchLessonsForSubject(subject.subject_id, token);
    //                     newLessonsMap[subject.subject_id] = lessonsData;
    //                 })
    //             );
    //         })
    //     );
    //     setLessonsMap(newLessonsMap);
    // };

    useEffect(() => {
        if (studentsData && studentsData.length === 0) return;
        const token = localStorage.getItem('token');
        fetchSubjectsForAll(token);
    }, [studentsData]);

    return {
        studentsData,
        subjectsMap,
        lessonsMap,
        fetchSubjectsForAll,

    }
}

export default usegetParentStudent
