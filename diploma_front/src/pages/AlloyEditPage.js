import React from "react";
import AlloyForm from "../components/alloys/AlloyForm";

const AlloyEditPage = () => {
  return (
    <div className="alloy-edit-page">
      <AlloyForm isEdit={true} />
    </div>
  );
};

export default AlloyEditPage;
