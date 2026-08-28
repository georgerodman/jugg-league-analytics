import type {ReactNode} from "react";
import styles from "./ResearchWriteup.module.css";

export type ResearchWriteupSource={url:string;title:string};

type Props={
  id?:string;
  name:string;
  positionPrice:string;
  playerMeta:string;
  controls?:ReactNode;
  positiveCount:number;
  negativeCount:number;
  independentOpinionCount:number;
  pros:string;
  cons:string;
  fullWriteup:string;
  context?:ReactNode;
  sources?:ResearchWriteupSource[];
  indexHref?:string;
  onClose?:()=>void;
  variant?:"page"|"modal";
};

export function ResearchWriteup({id,name,positionPrice,playerMeta,controls,positiveCount,negativeCount,independentOpinionCount,pros,cons,fullWriteup,context,sources=[],indexHref,onClose,variant="page"}:Props){
  const outlook=positiveCount>0&&negativeCount>0?"Mixed":positiveCount>0?"Positive":negativeCount>0?"Negative":null;
  return <article className={`${styles.writeup} ${variant==="modal"?styles.modal:""}`} id={id}>
    {onClose&&<button type="button" className={styles.close} aria-label="Close full writeup" onClick={onClose}>×</button>}
    <header className={styles.header}><div><h3>{name}<span>{positionPrice}</span></h3><p>{playerMeta}</p></div>{controls}</header>
    <p className={styles.opinions}>{positiveCount} positive · {negativeCount} negative · {independentOpinionCount} independent opinion{independentOpinionCount===1?"":"s"}{outlook&&<span className={styles[`outlook${outlook}`]}>{outlook}</span>}</p>
    <div className={styles.cases}><div><strong>Pros:</strong> {pros}</div><div><strong>Cons:</strong> {cons}</div></div>
    {context}
    <div className={styles.fullWriteup}>{fullWriteup.split(/\n\s*\n/).map((paragraph,index)=><p key={index}>{paragraph}</p>)}</div>
    {(sources.length>0||indexHref)&&<footer className={styles.footer}>{sources.length>0&&<strong>Sources</strong>}{sources.map(source=><a href={source.url} target="_blank" rel="noreferrer" key={source.url}>{source.title}</a>)}{indexHref&&<a className={styles.indexLink} href={indexHref}>Index ↑</a>}</footer>}
  </article>;
}
