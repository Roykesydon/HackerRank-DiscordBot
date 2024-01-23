from typing import List, Dict, Any, Tuple, Union

from dotenv import load_dotenv
from langchain.chains.qa_with_sources import load_qa_with_sources_chain
from langchain_openai import ChatOpenAI

from langchain_community.llms.huggingface_pipeline import HuggingFacePipeline
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline

from VDB_API.utils import file_processor
from VDB_API.utils.config import (
    PROMPT_TEMPLATE,
    CONTINUE_SEARCH_WORD,
    CHAT_MODELS,
    DEVICE,
)
from VDB_API.vectordb_manager import VectordbManager

load_dotenv()  # 加載.env檔案


class HackerRankTools:
    def __init__(self):
        self.llm = ChatOpenAI(temperature=0, model_name=CHAT_MODELS["gpt3"])
        self.chain = load_qa_with_sources_chain(self.llm, chain_type="map_reduce")
        self.vectordb_manager = VectordbManager()
        self.secondary_search = True
        self.tokenizer = AutoTokenizer.from_pretrained(
            CHAT_MODELS["offline"], trust_remote_code=True
        )

    def set_llm_type(self, llm_type: str):
        if llm_type in CHAT_MODELS.keys():
            if llm_type == "offline":
                print("Your device: ", DEVICE)
                model = AutoModelForCausalLM.from_pretrained(
                    CHAT_MODELS["offline"]
                ).eval()
                pipe = pipeline(
                    "text-generation",
                    model=model.to(DEVICE),
                    tokenizer=self.tokenizer,
                    max_new_tokens=100,
                )
                self.llm = HuggingFacePipeline(pipeline=pipe)
            else:
                self.llm = ChatOpenAI(temperature=0, model_name=CHAT_MODELS[llm_type])
        else:
            print("Model type not found, keeping it unchanged.")

        self.chain = load_qa_with_sources_chain(self.llm, chain_type="map_reduce")
        print("set chat model to ", CHAT_MODELS[llm_type])

    def set_secondary_search(self, secondary_search: bool):
        self.secondary_search = secondary_search
        print("set secondary_search to ", secondary_search)

    def add_documents_to_vdb(self, file_paths: List[str]):
        """
        Arg:
            file_paths: 文件路徑 list (需含檔名)
        """
        for file_path in file_paths:
            texts = file_processor.get_split_data(file_path)
            self.vectordb_manager.add(texts)

    # 刪除 _collection 裡的指定資料
    def delete(self, fileNameList) -> List[str]:
        """
        Arg:
            fileNameList: list of specified reference file names
        Returns:
            fileNameList: list of deleted file names
        """
        if len(fileNameList) == 1:
            where = {"source": fileNameList[0]}
        else:
            where = {"$or": [{"source": name} for name in fileNameList]}
        self.vectordb_manager.delete(where=where)
        print(f"刪除 {fileNameList} 相關資料")
        return fileNameList

    # 模型問答
    def chat(
        self, query, all_accessible_files, specified_files=None
    ) -> Tuple[str, Union[List[str], None], Union[List[dict], None]]:
        """
        Args:
            query: user query
            all_accessible_files: list of all accessible file names
            specified_files: list of specified reference file names
        Returns:
            ans: model reply
            contents: list of reference document paragraphs
            metadatas: list of reference document info
                pdf: {'source': 檔名, 'page': 頁碼}
                txt: {'source': 檔名}
        """
        # contents = set()
        # metadatas = set() # bug: 會過度刪除，變成長度與 contents 不同
        contents, metadatas = [], []

        if specified_files is None:
            docs, tmp_contents, tmp_metadatas = self._search_vdb(
                query, all_accessible_files
            )
        else:
            docs, tmp_contents, tmp_metadatas = self._search_vdb(query, specified_files)
        contents.extend(tmp_contents)
        metadatas.extend(tmp_metadatas)
        ans = self._get_llm_reply(query, docs)

        # 二次搜索
        if (
            self.secondary_search
            and (specified_files != None)
            and (CONTINUE_SEARCH_WORD in ans)
        ):
            # 快速問答不應觸發到這裡
            print("\n有其他參考資料需要，進行二次搜索...")
            docs, tmp_contents, tmp_metadatas = self._search_vdb(
                query, all_accessible_files
            )
            contents.extend(tmp_contents)
            metadatas.extend(tmp_metadatas)
            ans = self._get_llm_reply(query, docs)

        return ans, contents, metadatas

    def _get_filter(self, file_list) -> Union[Dict[str, Any], None]:
        if len(file_list) == 1:
            return {"source": file_list[0]}
        elif len(file_list) > 1:
            return {"$or": [{"source": name} for name in file_list]}
        else:
            raise ValueError("file_list is empty")

    def _search_vdb(self, query, file_list):
        where = self._get_filter(file_list)
        docs = self.vectordb_manager.query(query, n_results=3, where=where)

        contents, metadatas = [], []
        for doc in docs:
            contents.append(doc.page_content)
            metadatas.append(doc.metadata)

        return docs, contents, metadatas

    def _get_llm_reply(self, query, docs):
        templated_query = PROMPT_TEMPLATE.format(query=query)
        ans = self.chain.invoke(
            {"input_documents": docs, "question": templated_query},
            return_only_outputs=True,
        )["output_text"]
        ans = ans.split("\nSOURCES:")[0]
        return ans
