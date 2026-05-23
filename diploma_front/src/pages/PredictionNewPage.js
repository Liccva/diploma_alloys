import React from "react";
import PredictionForm from "../components/predictions/PredictionForm";

const PredictionNewPage = () => {
  return (
    <div className="prediction-new-page">
      <div className="page-header">
        <h1>Создание нового прогноза</h1>
      </div>
      <PredictionForm isEdit={false} />
    </div>
  );
};

export default PredictionNewPage;