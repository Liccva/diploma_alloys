import React from "react";
import { useParams } from "react-router-dom";
import PredictionForm from "../components/predictions/PredictionForm";

const PredictionEditPage = () => {
  const { id } = useParams();

  return (
    <div className="prediction-edit-page">
      <div className="page-header">
        <h1>Редактирование прогноза #{id}</h1>
      </div>
      <PredictionForm isEdit={true} />
    </div>
  );
};

export default PredictionEditPage;