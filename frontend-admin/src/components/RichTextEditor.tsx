import ReactQuill from "react-quill-new";
import "react-quill-new/dist/quill.snow.css";

interface Props {
  value: string;
  onChange: (val: string) => void;
}

export function RichTextEditor({ value, onChange }: Props) {
  const modules = {
    toolbar: [
      ["bold", "italic", "underline", "strike"],
      [{ list: "ordered" }, { list: "bullet" }],
      ["link"],
      ["clean"],
    ],
  };

  return (
    <div className="bg-white">
      <ReactQuill theme="snow" value={value} onChange={onChange} modules={modules} />
    </div>
  );
}
