import React from "react";
import PatentForm from "../components/patents/PatentForm";

const PatentEditPage = () => {
  return (
    <div className="patent-edit-page">
      <PatentForm isEdit={true} />
    </div>
  );
};

export default PatentEditPage;
