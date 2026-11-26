const { createApp, ref, computed } = Vue;

createApp({
  setup() {
    const question = ref("");
    const selectedFile = ref(null);
    const uploading = ref(false);
    const documentId = ref(null);
    const documentStatus = ref("当前使用默认退款资料。");
    const activeDocumentName = ref("退款政策（示例）");
    const asking = ref(false);
    const answer = ref("");
    const hits = ref([]);
    const requestStatus = ref("");
    const requestState = ref("idle");
    const examples = ["退款多久到账？", "申请退款需要满足哪些条件？", "客服的服务时间是什么？"];

    const cleanQuestion = computed(() => {
      return question.value.trim();
    });

    const answerParts = computed(() => {
      return answer.value
        .split(/(\[[0-9]+\])/g)
        .filter(text => text !== "")
        .map(text => {
          const match = text.match(/^\[([0-9]+)\]$/);
          const number = match ? Number(match[1]) : null;

          return {
            text,
            number: (
              number !== null
              && number >= 1
              && number <= hits.value.length
            ) ? number : null,
          };
        });
    });

    function clearQuestion() {
      question.value = "";
    }

    function selectFile(event) {
      selectedFile.value = event.target.files[0] ?? null;
    }

    async function readJsonResponse(response) {
      const data = await response.json();

      if (!response.ok) {
        const message = typeof data.detail === "string"
          ? data.detail
          : `请求失败（${response.status}）`;
        throw new Error(message);
      }

      return data;
    }

    async function uploadAndIndex() {
      if (!selectedFile.value || uploading.value || asking.value) {
        return;
      }

      uploading.value = true;

      try {
        documentStatus.value = "正在上传…";
        const form = new FormData();
        form.append("file", selectedFile.value);

        const uploadResponse = await fetch("/api/upload", {
          method: "POST",
          body: form,
        });
        const uploaded = await readJsonResponse(uploadResponse);

        documentStatus.value = "上传完成，正在建库…";
        const indexResponse = await fetch("/api/index", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ document_id: uploaded.document_id }),
        });
        const indexed = await readJsonResponse(indexResponse);

        documentId.value = uploaded.document_id;
        activeDocumentName.value = uploaded.filename;
        documentStatus.value =
          `当前资料：${uploaded.filename}，共 ${indexed.chunk_count} 个片段。`;
      } catch (error) {
        documentStatus.value = `处理失败：${error.message}。当前资料未切换。`;
      } finally {
        uploading.value = false;
      }
    }

    async function readSseResponse(response, onEvent) {
      if (!response.body) {
        throw new Error("响应没有可读取的数据流");
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      try {
        while (true) {
          const { value, done } = await reader.read();
          buffer += decoder.decode(value, { stream: !done });
          buffer = buffer.replace(/\r\n/g, "\n");

          let boundary;
          while ((boundary = buffer.indexOf("\n\n")) !== -1) {
            const frame = buffer.slice(0, boundary);
            buffer = buffer.slice(boundary + 2);
            const lines = frame.split("\n");
            const eventLine = lines.find(line => line.startsWith("event:"));
            const dataLines = lines.filter(line => line.startsWith("data:"));

            if (dataLines.length === 0) {
              continue;
            }

            const event = eventLine ? eventLine.slice(6).trim() : "message";
            const data = dataLines
              .map(line => line.slice(5).trimStart())
              .join("\n");

            onEvent(event, JSON.parse(data));
          }

          if (done) {
            if (buffer.trim()) {
              throw new Error("数据流结束时存在不完整事件");
            }
            break;
          }
        }
      } finally {
        reader.releaseLock();
      }
    }

    async function askQuestion() {
      if (!cleanQuestion.value || asking.value || uploading.value) {
        return;
      }

      asking.value = true;
      answer.value = "";
      hits.value = [];
      requestStatus.value = "正在连接…";
      requestState.value = "processing";

      try {
        const response = await fetch("/api/ask/stream", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            question: cleanQuestion.value,
            top_k: 3,
            document_id: documentId.value,
          }),
        });

        if (!response.ok) {
          await readJsonResponse(response);
        }

        let receivedResult = false;

        await readSseResponse(response, (event, data) => {
          if (event === "progress") {
            requestStatus.value = data.message || "正在处理…";
          } else if (event === "result") {
            receivedResult = true;
            requestState.value = data.status;
            answer.value = data.answer;
            hits.value = data.hits;

            const labels = {
              answered: "回答完成",
              refused: "资料不足，已拒答",
              blocked: "回答未通过审核，已拦截",
            };
            requestStatus.value = labels[data.status] || "处理完成";
          } else if (event === "error") {
            throw new Error(data.message || "问答处理失败");
          }
        });

        if (!receivedResult) {
          throw new Error("连接已结束，但没有收到最终结果");
        }
      } catch (error) {
        answer.value = "";
        hits.value = [];
        requestStatus.value = `问答失败：${error.message}`;
        requestState.value = "error";
      } finally {
        asking.value = false;
      }
    }

    return {
      question,
      cleanQuestion,
      answerParts,
      clearQuestion,
      selectedFile,
      uploading,
      documentId,
      documentStatus,
      activeDocumentName,
      requestState,
      examples,
      selectFile,
      uploadAndIndex,
      asking,
      answer,
      hits,
      requestStatus,
      askQuestion,
    };
  },
}).mount("#app");
